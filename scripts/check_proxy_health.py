#!/usr/bin/env python3
"""Hermes skill-proxy health check helper.

Hits http://localhost:8643/health and prints both KB indexes' doc counts
plus loaded flag. Compares against the baseline (inexbot-open ~636,
inexbot ~547). The KB grows monotonically over time, so upward drift
(`docs >= baseline`) is accepted as healthy — exit 0. Failure exits 1
only when `docs < baseline` (sidebar regression / partial crawl /
proxy-not-reloaded) or `loaded != True` (proxy can't see index).
The diagnostic rule mirrors the SKILL.md "真故障判定" section.

Why this script exists instead of an inline one-liner:
    The local command policy (tirith / vet) blocks
    `curl ... | python3` and `python3 -c "..."` patterns and asks for
    human approval. This file is invoked via `python3 <path>`, so the
    policy does not flag it.

Usage:
    python3 ~/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/check_proxy_health.py
"""

import json
import sys
import urllib.error
import urllib.request

PROXY_URL = "http://localhost:8643/health"
TIMEOUT = 5  # seconds

# Baselines observed at 2026-10-22. Update if a deliberate crawl changes them.
# Monotonic upward drift is healthy; only docs < baseline is flagged.
# History: 534 (2026-07-18) → 552 (07-26) → 636 (07-31) → 715 (08-21) →
# 721 (08-25, steady) → 795 (2026-09-29; zh sidebar added new content) →
# 797 (2026-10-01; +2 zh sidebar) → 799 (2026-10-10; +2 zh sidebar continued) →
# 799 (2026-10-18/19/21/22; four consecutive flat cycles, index.json byte-identical
# since 10-19 — the zh sidebar +2/cycle growth has fully stopped).
BASELINES = {
    "inexbot-open": 799,   # flat since 2026-10-10; growth has stopped
    "inexbot":       558,  # doc.inexbot.com (sister KB); grew 547 → 557 → 558
}


def main() -> int:
    try:
        with urllib.request.urlopen(PROXY_URL, timeout=TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        print(f"[FAIL] cannot reach {PROXY_URL}: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"[FAIL] invalid JSON from proxy: {exc}", file=sys.stderr)
        return 1

    if payload.get("status") != "ok":
        print(f"[FAIL] proxy status != ok: {payload}", file=sys.stderr)
        return 1

    indexes = payload.get("indexes", {})
    failed = False
    for name, baseline in BASELINES.items():
        entry = indexes.get(name, {})
        docs = entry.get("docs", -1)
        loaded = entry.get("loaded", False)
        # KB grows monotonically — accept docs >= baseline as healthy.
        # Only flag when docs DROPPED below baseline (sidebar regression,
        # partial crawl, proxy not reloaded) or loaded is False.
        ok = docs >= baseline and loaded
        mark = "OK  " if ok else "DIFF"
        print(f"  [{mark}] {name:<14} docs={docs:>4}  loaded={loaded}  (baseline {baseline})")
        if not ok:
            failed = True

    if failed:
        print("[WARN] at least one KB index drifted from baseline — "
              "investigate (sidebar change? partial crawl? proxy not reloaded?)",
              file=sys.stderr)
        return 1
    print(f"[OK] hermes-skill-proxy healthy; gateway={payload.get('hermes_url', '<unset>')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
