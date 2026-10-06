#!/usr/bin/env python
"""Static-analysis scan of a Sourcify-verified EVM contract.

Usage: scanner.py <chainId> <address>
Prints one JSON object to stdout. Runs Slither detectors on the verified
source (following a proxy to its implementation) and lists functions that
are gated by owner/role checks, which is where admin risk lives.
"""
import json
import os
import re
import sys
import tempfile
import time
import urllib.request

from slither import Slither
from slither.detectors import all_detectors
from slither.detectors.abstract_detector import AbstractDetector, DetectorClassification

SOURCIFY = "https://sourcify.dev/server/v2/contract"
CHAINS = {
    "1": "Ethereum", "8453": "Base", "42161": "Arbitrum One", "10": "Optimism",
    "137": "Polygon", "56": "BNB Chain", "43114": "Avalanche", "11155111": "Sepolia",
    "84532": "Base Sepolia", "324": "zkSync Era", "59144": "Linea", "534352": "Scroll",
    "81457": "Blast", "130": "Unichain", "100": "Gnosis",
}
IMPACT_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Informational": 3, "Optimization": 4}
PRIV_HINT = re.compile(r"owner|admin|role|auth|governor|guardian|operator|minter|pauser", re.I)


def fetch_meta(chain, addr):
    url = f"{SOURCIFY}/{chain}/{addr}?fields=compilation,proxyResolution"
    req = urllib.request.Request(url, headers={"User-Agent": "contractscan/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def detector_classes():
    out = []
    for name in dir(all_detectors):
        obj = getattr(all_detectors, name)
        if isinstance(obj, type) and issubclass(obj, AbstractDetector):
            if obj.IMPACT in (DetectorClassification.OPTIMIZATION,):
                continue
            out.append(obj)
    return out


def privileged_functions(sl, main_name):
    found = []
    for c in sl.contracts:
        if c.name != main_name:
            continue
        for f in c.functions_entry_points:
            if f.is_constructor or f.view or f.pure:
                continue
            mods = [m.name for m in f.modifiers]
            gated = any(PRIV_HINT.search(m) for m in mods)
            if not gated:
                # msg.sender compared against a state variable, e.g. require(msg.sender == owner)
                gated = any("msg.sender" in str(n) and PRIV_HINT.search(str(n)) for n in f.nodes)
            if gated:
                found.append({"function": f.full_name, "modifiers": mods})
    return found


def scan(chain, addr):
    t0 = time.time()
    if chain not in CHAINS and not chain.isdigit():
        return {"ok": False, "error": "chainId must be numeric, e.g. 8453 for Base"}
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", addr):
        return {"ok": False, "error": "address must be a 0x-prefixed 20-byte hex address"}
    meta = fetch_meta(chain, addr)
    if not meta:
        return {"ok": False, "error": "contract is not verified on Sourcify for this chain; nothing to analyse",
                "chainId": chain, "address": addr}
    report = {
        "ok": True,
        "chainId": chain,
        "chain": CHAINS.get(chain, f"chain {chain}"),
        "address": addr,
        "contractName": meta["compilation"]["name"],
        "compiler": meta["compilation"]["compilerVersion"],
        "sourcifyMatch": meta.get("match"),
        "proxy": None,
    }
    target_addr = addr
    target_name = meta["compilation"]["name"]
    pr = meta.get("proxyResolution") or {}
    if pr.get("isProxy") and pr.get("implementations"):
        impl = pr["implementations"][0]
        report["proxy"] = {"type": pr.get("proxyType"), "implementation": impl.get("address"),
                           "implementationName": impl.get("name"),
                           "note": "Upgradeable: whoever controls the proxy admin can replace this code."}
        imeta = fetch_meta(chain, impl["address"])
        if imeta:
            target_addr = impl["address"]
            target_name = imeta["compilation"]["name"]
            report["analysedImplementation"] = True
        else:
            report["analysedImplementation"] = False
    with tempfile.TemporaryDirectory(prefix="cscan-") as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            sl = Slither(f"sourcify-{chain}:{target_addr}", export_dir=os.path.join(d, "crytic-export"))
            for cls in detector_classes():
                sl.register_detector(cls)
            raw = [r for batch in sl.run_detectors() for r in batch]
            priv = privileged_functions(sl, target_name)
        finally:
            os.chdir(cwd)
    findings = []
    for r in raw:
        desc = re.sub(r"\(/?[^()]*?/([^/()]+\.sol)#", r"(\1#", r["description"]).strip()
        findings.append({"check": r["check"], "impact": r["impact"], "confidence": r["confidence"],
                         "description": desc[:600]})
    findings.sort(key=lambda f: (IMPACT_ORDER.get(f["impact"], 9), f["confidence"] != "High"))
    counts = {}
    for f in findings:
        counts[f["impact"]] = counts.get(f["impact"], 0) + 1
    report.update({
        "analysedContract": target_name,
        "summary": {"findingsByImpact": counts, "privilegedFunctionCount": len(priv)},
        "privilegedFunctions": priv[:60],
        "findings": findings[:80],
        "engine": "Slither static analysis on Sourcify-verified source",
        "disclaimer": "Automated static analysis. Not a manual audit; review findings before acting.",
        "seconds": round(time.time() - t0, 1),
    })
    return report


if __name__ == "__main__":
    try:
        out = scan(sys.argv[1], sys.argv[2])
    except Exception as e:  # report failures as JSON so the API can relay them
        out = {"ok": False, "error": f"analysis failed: {type(e).__name__}: {str(e)[:300]}"}
    sys.stdout.write(json.dumps(out))
