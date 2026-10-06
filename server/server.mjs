// ContractLens: pay-per-call smart contract static analysis over x402.
// Buyers pay USDC on Base (or Arbitrum); a failed or unverifiable scan returns 4xx/5xx and is never settled.
import express from "express";
import { execFile } from "node:child_process";
import { appendFileSync, readFileSync } from "node:fs";
import { paymentMiddleware, x402ResourceServer } from "@x402/express";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { declareDiscoveryExtension } from "@x402/extensions/bazaar";

const PORT = Number(process.env.PORT || 4021);
const PAY_TO = "0x36c37d1b47737ba2b2a2cf1b5bc38509516b222f";
const FACILITATOR = process.env.FACILITATOR_URL || "https://facilitator.payai.network";
const PUBLIC_URL = (process.env.PUBLIC_URL || `http://localhost:${PORT}`).replace(/\/$/, "");
const PRICE = process.env.SCAN_PRICE || "$0.05";
const PY = `${process.env.HOME}/.local/share/uv/tools/slither-analyzer/bin/python`;
const SCANNER = new URL("./scanner.py", import.meta.url).pathname;
const LOG = new URL("./requests.log", import.meta.url).pathname;
const SAMPLE = JSON.parse(readFileSync(new URL("./sample-report.json", import.meta.url)));

const cache = new Map(); // `${chain}:${addr}` -> {at, report}
let running = 0;

function log(obj) {
  try { appendFileSync(LOG, JSON.stringify({ t: new Date().toISOString(), ...obj }) + "\n"); } catch {}
}

function runScan(chain, addr) {
  const key = `${chain}:${addr.toLowerCase()}`;
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < 6 * 3600e3) return Promise.resolve(hit.report);
  return new Promise((resolve) => {
    running++;
    execFile(PY, [SCANNER, chain, addr], { timeout: 170e3, maxBuffer: 8e6, cwd: "/tmp" }, (err, stdout) => {
      running--;
      let report;
      try { report = JSON.parse(stdout); } catch { report = { ok: false, error: err ? `analysis failed: ${err.message.slice(0, 200)}` : "analysis failed" }; }
      if (report.ok) cache.set(key, { at: Date.now(), report });
      resolve(report);
    });
  });
}

const inputSchema = {
  properties: {
    chainId: { type: "string", description: "EVM chain id: 1 Ethereum, 8453 Base, 42161 Arbitrum, 10 Optimism, 137 Polygon, 56 BNB" },
    address: { type: "string", description: "Contract address (0x...). Must be verified on Sourcify. Proxies are followed to the implementation." },
  },
  required: ["chainId", "address"],
};
const outputExample = {
  ok: true, chain: "Base", address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", contractName: "FiatTokenProxy",
  proxy: { type: "ZeppelinOSProxy", implementation: "0x2Ce6311ddAE708829bc0784C967b7d77D19FD779" },
  summary: { findingsByImpact: { Low: 9, Informational: 35 }, privilegedFunctionCount: 11 },
  privilegedFunctions: [{ function: "mint(address,uint256)", modifiers: ["onlyMinters"] }],
  findings: [{ check: "shadowing-local", impact: "Low", confidence: "High", description: "..." }],
};
const description =
  "Smart contract security scan for AI agents: give a chain id and contract address, get Slither static-analysis findings " +
  "(reentrancy, unchecked calls, arbitrary sends, etc.), proxy/upgradeability status and the list of owner/role-gated admin functions " +
  "(mint, pause, blacklist, upgrade). Works on any Sourcify-verified contract on Ethereum, Base, Arbitrum, Optimism, Polygon, BNB. " +
  "Use before approving, depositing into or trading a token/protocol. Unverified contracts are rejected without charge.";

const accepts = [
  { scheme: "exact", price: PRICE, network: "eip155:8453", payTo: PAY_TO, maxTimeoutSeconds: 300 },
  { scheme: "exact", price: PRICE, network: "eip155:42161", payTo: PAY_TO, maxTimeoutSeconds: 300 },
];

const routes = {
  "GET /scan": {
    accepts,
    description,
    mimeType: "application/json",
    extensions: {
      ...declareDiscoveryExtension({ input: { chainId: "8453", address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" }, inputSchema, output: { example: outputExample } }),
    },
  },
};

const facilitator = new HTTPFacilitatorClient({ url: FACILITATOR });
const server = new x402ResourceServer(facilitator)
  .register("eip155:8453", new ExactEvmScheme())
  .register("eip155:42161", new ExactEvmScheme());

const app = express();
app.set("trust proxy", true);

app.use((req, res, next) => {
  const paid = Boolean(req.get("payment-signature") || req.get("x-payment"));
  res.on("finish", () => log({ m: req.method, p: req.originalUrl.slice(0, 200), s: res.statusCode, paid, ua: (req.get("user-agent") || "").slice(0, 120) }));
  next();
});

// Reject bad input before the paywall so nobody pays for a request that cannot succeed.
app.get("/scan", async (req, res, next) => {
  const chainId = String(req.query.chainId || "");
  const address = String(req.query.address || "");
  if (!chainId && !address) return next(); // bare probe: show the 402 challenge
  if (!/^\d+$/.test(chainId) || !/^0x[0-9a-fA-F]{40}$/.test(address)) {
    return res.status(400).json({ ok: false, error: "query params required: chainId (numeric) and address (0x + 40 hex)" });
  }
  next();
});

app.use(paymentMiddleware(routes, server, { appName: "ContractLens", testnet: false }));

app.get("/scan", async (req, res) => {
  const chainId = String(req.query.chainId || "");
  const address = String(req.query.address || "");
  if (running >= 3) return res.status(503).json({ ok: false, error: "busy, retry in a minute (you were not charged)" });
  const report = await runScan(chainId, address);
  if (!report.ok) return res.status(422).json(report);
  res.json(report);
});

app.get("/sample", (req, res) => res.json(SAMPLE));
app.get("/health", (req, res) => res.json({ ok: true, running }));

const openapi = () => ({
  openapi: "3.1.0",
  info: { title: "ContractLens", version: "1.0.0", description, "x-guidance": "Call GET /scan?chainId=8453&address=0x... ; pay with x402 (USDC on Base or Arbitrum). Free sample at /sample." },
  servers: [{ url: PUBLIC_URL }],
  paths: {
    "/scan": {
      get: {
        operationId: "scanContract",
        summary: "Static-analysis security scan of a verified EVM contract",
        description,
        parameters: [
          { name: "chainId", in: "query", required: true, schema: inputSchema.properties.chainId, example: "8453" },
          { name: "address", in: "query", required: true, schema: inputSchema.properties.address, example: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" },
        ],
        "x-payment-info": { protocols: ["x402"], price: { mode: "fixed", currency: "USD", amount: PRICE.replace("$", "") }, pricingMode: "fixed", price_usd: PRICE.replace("$", "") },
        responses: {
          200: { description: "Scan report", content: { "application/json": { example: outputExample } } },
          402: { description: "Payment Required" },
          422: { description: "Contract not verified on Sourcify or analysis failed (not charged)" },
        },
      },
    },
    "/sample": { get: { operationId: "sampleReport", summary: "Free sample report (USDC on Base)", responses: { 200: { description: "Sample" } } } },
  },
});
app.get("/openapi.json", (req, res) => res.json(openapi()));
app.get("/.well-known/openapi.json", (req, res) => res.json(openapi()));
app.get("/.well-known/x402", (req, res) => res.json({ version: 1, resources: [`${PUBLIC_URL}/scan`], description }));

app.get("/", (req, res) => {
  res.type("html").send(`<!doctype html><meta charset=utf-8><title>ContractLens: smart contract scans for AI agents (x402)</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>body{font:16px/1.5 system-ui;max-width:760px;margin:40px auto;padding:0 16px;color:#111}code,pre{background:#f3f3f3;padding:2px 4px;border-radius:4px}pre{padding:12px;overflow:auto}</style>
<h1>ContractLens</h1>
<p>Pay-per-call smart contract security scan, built for AI agents and the developers who run them. One HTTP call, ${PRICE} in USDC via <a href="https://x402.org">x402</a> on Base or Arbitrum. No API key, no signup.</p>
<p>Give it a chain id and a contract address. It pulls the verified source from Sourcify, follows proxies to the implementation, runs Slither's detectors, and lists every owner/role-gated function (mint, pause, blacklist, upgrade). Unverified contracts are rejected <b>before</b> payment.</p>
<pre>GET ${PUBLIC_URL}/scan?chainId=8453&amp;address=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913</pre>
<p>Try it from a terminal with an x402 client, e.g. <code>npx agentcash fetch "${PUBLIC_URL}/scan?chainId=8453&amp;address=0x..."</code>. Free sample output: <a href="/sample">/sample</a>. OpenAPI: <a href="/openapi.json">/openapi.json</a>.</p>
<p>Automated static analysis, not a manual audit. Built by DeFi engineers who have shipped audited protocols.</p>`);
});

app.listen(PORT, () => console.log(`ContractLens on :${PORT}, public ${PUBLIC_URL}, facilitator ${FACILITATOR}`));
