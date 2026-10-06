# ContractLens

**Check a smart contract before your agent touches it.** Who holds the keys right now (owner and proxy admin: renounced, single-key EOA or Safe multisig), every owner- or role-gated function (mint, pause, blacklist, upgrade, fees), proxy status, and Slither static-analysis findings ranked by impact. It works on any Sourcify-verified contract on Ethereum, Base, Arbitrum, Optimism, Polygon and BNB Chain.

- **Web (free):** https://swarm-t3.github.io/contractlens/
- **Remote MCP server (free, 30 scans/day):** `<LIVE_URL>/mcp` (Streamable HTTP, stateless), with tool `scan_contract(chainId, address)`
- **x402 API (pay per call):** `GET <LIVE_URL>/scan?chainId=8453&address=0x...` costs **$0.01 USDC** on Base or Arbitrum. No API key and no signup.
- **Free preview:** `GET <LIVE_URL>/preview?chainId=...&address=...`. Sample report at `/sample`, OpenAPI at `/openapi.json`, public counters at `/stats`.
- **Agent skill:** [`skills/contractlens/SKILL.md`](skills/contractlens/SKILL.md) for Bankr, OpenClaw and Claude agents.

`<LIVE_URL>` is the current origin in [`LIVE_URL`](LIVE_URL). It is a Cloudflare tunnel for now and moves to a permanent host soon. Read it programmatically:

```bash
BASE=$(curl -s https://raw.githubusercontent.com/swarm-t3/contractlens/main/LIVE_URL)
```

## MCP setup

Claude Code:
```bash
claude mcp add --transport http contractlens "$(curl -s https://raw.githubusercontent.com/swarm-t3/contractlens/main/LIVE_URL)/mcp"
```

Cursor and other clients (`mcp.json`):
```json
{ "mcpServers": { "contractlens": { "url": "<LIVE_URL>/mcp" } } }
```

Then ask your client something like "Is 0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed on Base safe to hold? Who can mint?"

## Pay-per-call (x402)

```bash
npx agentcash fetch "$BASE/scan?chainId=8453&address=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
```

Bad input and unverified contracts are rejected before the 402. A scan that fails is never settled. Payments go to `0x36c37d1b47737ba2b2a2cf1b5bc38509516b222f` via the PayAI facilitator, and every settled payment is listed at `/stats` with its transaction hash.

## Code

- `server/scanner.py`: Slither on Sourcify-verified source, proxy resolution, privileged-function extraction, owner and admin classification over public RPCs.
- `server/server.mjs`: Express with `@x402/express` (v2), free preview, MCP endpoint, OpenAPI and stats.
- `deploy/hf/`: Dockerfile for a Hugging Face Docker Space.

This is automated static analysis, not a manual audit. Expect false positives.
