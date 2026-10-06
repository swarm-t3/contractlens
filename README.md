# ContractLens

Pay-per-call smart contract security scan for AI agents, sold over [x402](https://x402.org).

- `GET /scan?chainId=8453&address=0x...` returns Slither static-analysis findings, proxy/upgradeability status and the owner/role-gated admin functions (mint, pause, blacklist, upgrade) of any Sourcify-verified contract on Ethereum, Base, Arbitrum, Optimism, Polygon or BNB Chain.
- Price: $0.01 in USDC, paid with an x402 client on Base (eip155:8453) or Arbitrum One (eip155:42161). No API key, no signup.
- Unverified contracts and bad input are rejected before payment; failed scans are never settled.
- Free sample report: `/sample`. OpenAPI: `/openapi.json`.

Live endpoint: see `LIVE_URL` in this repo (the host is a Cloudflare quick tunnel and can change on restart).

Code: `server/server.mjs` (Express + `@x402/express`, PayAI facilitator), `server/scanner.py` (Slither + Sourcify).

Automated static analysis, not a manual audit.
