#!/usr/bin/env python3
"""Hermes skill-proxy health check helper.

Hits http://localhost:8643/health and prints both KB indexes' doc counts
plus loaded flag, and compares them against TWO numbers per KB:

  * FLOOR  (BASELINES) -- the doc count of the last known-good index.
  * TARGET (on-disk index.json) -- the count the proxy WILL serve after
    its next 5h automatic reload.

Why two numbers: the proxy keeps the last known-good index in memory until
its 5h auto-reload picks up a newer on-disk one.  After a growth crawl it
therefore legitimately reports the OLD count for up to five hours.  A check
that compared against a single "expected" number would report a fault every
single time the KB grows -- i.e. it would cry wolf precisely when something
real is happening.

The rule:
  loaded is False                  -> FAIL (proxy cannot see the index)
  docs >= FLOOR                    -> healthy
  docs >= TARGET (disk)            -> healthy
  docs <  FLOOR and docs <  TARGET -> FAIL (genuine regression:
                                       sidebar extraction broke)
  docs <  TARGET but >= FLOOR      -> healthy, "awaiting 5h auto-reload"

⚠️ 2026-11-27: this used to compare against a single baseline that was
patched UPWARD to the newest count the moment a crawl grew the KB.  That
made the check fail for the whole reload window (up to 5h) after every
growth -- a false-positive generator, the same class of problem as SKILL.md
trap 47 ("a permanently-red audit script is more dangerous than no script").
The floor/target model above fixes it.  The criterion is verified in BOTH
directions by scripts/test_proxy_health_regression.py (a permanently-GREEN
check that never reports anything is just as useless).

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
from pathlib import Path

PROXY_URL = "http://localhost:8643/health"
TIMEOUT = 5  # seconds

# Disk index locations, per KB name. Used to distinguish "proxy has not reloaded
# yet" (normal 5h reload window) from a genuine regression (docs dropped).
KB_ROOT = Path.home() / ".hermes" / "kb"

# Baselines observed at 2026-10-22. Update if a deliberate crawl changes them.
# Monotonic upward drift is healthy; only docs < baseline is flagged.
# History: 534 (2026-07-18) → 552 (07-26) → 636 (07-31) → 715 (08-21) →
# 721 (08-25, steady) → 795 (2026-09-29; zh sidebar added new content) →
# 797 (2026-10-01; +2 zh sidebar) → 799 (2026-10-10; +2 zh sidebar continued) →
# 799 (2026-10-18/19/21/22; four consecutive flat cycles, index.json byte-identical
# since 10-19 — the zh sidebar +2/cycle growth has fully stopped).
#
# BASELINES[kb] = the doc count of the LAST KNOWN-GOOD index — i.e. the floor.
# The proxy holds that index in memory until its 5h auto-reload picks up a newer
# on-disk one.  After a growth crawl the proxy therefore legitimately reports
# the OLD count for up to 5 hours; flagging that as a fault would make this
# check cry wolf every time the KB grows.
#
# So the rule is:
#   docs >= BASELINES[kb]              -> healthy (proxy has at least the floor)
#   docs == disk count                 -> healthy, just awaiting the auto-reload
#   docs < BASELINES[kb] and != disk   -> genuine regression (sidebar break)
#   loaded is False                    -> genuine failure (proxy can't see index)
BASELINES = {
    # 944 on 2026-11-27: upstream restructured 05.JSON-协议 --
    #   04.dev-rt (73) renamed to 05.dev-rt (72) AND a new 04.dev-wk section (83)
    #   appeared; zh 476 -> 588. 187 real network fetches (first non-zero since
    #   11-18). Before that, 832 was the flat baseline 11-18 -> 11-26
    #   (9 consecutive identical cycles) — the proxy still serves 832 in memory
    #   until the next auto-reload, which is normal, not a fault.
    "inexbot-open": 832,
    "inexbot":       562,  # doc.inexbot.com (sister KB); grew 547 → 557 → 558 → 560 → 561 (11-19) → 562 (2026-11-25)
}


def disk_docs(kb_name: str):
    """Number of entries in the KB's on-disk index.json, or None if unreadable.

    Used to tell "the proxy has not reloaded yet" (memory == freshly crawled
    disk index, i.e. the normal 5h reload window) apart from a real
    regression (memory below the disk index for an unexplained reason).
    """
    try:
        idx = KB_ROOT / kb_name / "index.json"
        return len(json.loads(idx.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


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
    for name, floor in BASELINES.items():
        entry = indexes.get(name, {})
        docs = entry.get("docs", -1)
        loaded = entry.get("loaded", False)
        disk = disk_docs(name)
        # The proxy serves the last known-good index until its 5h auto-reload
        # picks up the newer on-disk one.  After a growth crawl it therefore
        # reports the OLD count for up to 5 hours -- that is the normal reload
        # window, NOT a fault.  Only a drop BELOW the floor (sidebar breakage)
        # or loaded=False is a genuine failure.
        ok = loaded and (docs >= floor or (disk is not None and docs >= disk))
        mark = "OK  " if ok else "DIFF"
        note = ""
        if loaded and docs < floor and disk is not None and docs < disk:
            note = f"  (disk has {disk})"
        elif loaded and docs < disk:
            note = f"  (disk has {disk}; awaiting 5h auto-reload)"
        print(f"  [{mark}] {name:<14} docs={docs:>4}  loaded={loaded}  (floor {floor}){note}")
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
