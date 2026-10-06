---
name: contractlens
description: |
  Check a smart contract before your agent approves, deposits into, or buys a token on it.
  Returns who can mint, pause, blacklist or upgrade (owner/role-gated functions), whether it is an
  upgradeable proxy and which implementation is live, and Slither static-analysis findings ranked by impact.
  Works on any Sourcify-verified contract on Base, Ethereum, Arbitrum, Optimism, Polygon and BNB Chain.
  Triggers: "is this token safe", "can the owner mint", "check this contract", "who controls 0x...",
  "is this upgradeable", "audit this address", any pre-trade or pre-approval due diligence.
  Payment: x402, $0.01 USDC per call on Base or Arbitrum. No API key, no account.
---

# ContractLens

Pay-per-call smart contract scan for agents.

**Base URL:** read the current origin from `https://raw.githubusercontent.com/swarm-t3/contractlens/main/LIVE_URL`
**Web:** https://swarm-t3.github.io/contractlens/
**Payment:** x402 v2, exact scheme, USDC on Base (`eip155:8453`) or Arbitrum One (`eip155:42161`), $0.01 per call.

## Endpoints

| Endpoint | Price | Returns |
|---|---|---|
| `GET /scan?chainId=<id>&address=<0x...>` | $0.01 | Full report: proxy + implementation, every privileged function with its modifiers, all Slither findings (check, impact, confidence, file#line) |
| `GET /preview?chainId=<id>&address=<0x...>` | free (20/day/IP) | Counts by impact, names of High/Medium checks, first 3 privileged functions |
| `GET /sample` | free | Example full report (USDC on Base) |
| `GET /openapi.json` | free | OpenAPI 3.1 with x402 payment info |

Chain ids: 1 Ethereum, 8453 Base, 42161 Arbitrum, 10 Optimism, 137 Polygon, 56 BNB Chain.

Bad input and contracts that are not verified on Sourcify are rejected **before** the 402, so the agent is never charged for a scan that cannot run. A scan that fails after payment is not settled.

## How to call

```bash
BASE=$(curl -s https://raw.githubusercontent.com/swarm-t3/contractlens/main/LIVE_URL)
npx agentcash fetch "$BASE/scan?chainId=8453&address=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
```

```typescript
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
const pay = wrapFetchWithPaymentFromConfig(fetch, { schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(account) }] });
const report = await (await pay(`${BASE}/scan?chainId=8453&address=${token}`)).json();
```

## Reading the report

- `proxy` not null: the code can be replaced by whoever controls the proxy admin. Treat as a trust assumption.
- `privilegedFunctions`: look for `mint`, `pause`, `blacklist`/`setBlocked`, `setFee`/`setTax`, `upgradeTo`, `withdraw`/`rescue`. On a fresh memecoin, an owner-only `mint` or fee setter with no cap is the classic rug path.
- `findings`: sorted High, Medium, Low, Informational. Slither has false positives; High + High-confidence findings deserve a human look before you size up.
- `summary.findingsByImpact` gives a quick go/no-go signal.

Automated static analysis, not a manual audit.
