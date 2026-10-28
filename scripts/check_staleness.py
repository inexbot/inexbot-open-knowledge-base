#!/usr/bin/env python3
"""Detect cache entries that document content upstream has since removed.

WHY THIS EXISTS
---------------
crawler.py is incremental:

    if not force and raw_path.exists() and md_path.exists():
        <reuse cache>          # <- same-URL body edits are NEVER re-fetched

So a page whose upstream text changed but whose URL stayed the same is cached
forever. The worst case is a page RENAME: the renamed API shows correct content
in the locale whose URL also changed, while other locales keep documenting a
symbol that no longer exists upstream (observed 2026-10-23, star_servo_*).

METRIC (one direction only!)
----------------------------
    cache-only terms = tokens in md/<slug>.md that are ABSENT from live HTML

The reverse direction ("live has terms the cache lacks") is USELESS: every page
carries ~1100 site-chrome tokens (nav/sidebar/footer) that never make it into
the extracted markdown, so that metric flags 100% of pages as stale.

Usage:
    python3 scripts/check_staleness.py                 # deterministic sample
    python3 scripts/check_staleness.py --term star_    # hunt a specific token
    python3 scripts/check_staleness.py --sample 40     # wider sample

Exit codes:
    0 - no cache-only terms found in the sample
    1 - at least one stale page detected (needs cache invalidation)
    2 - index missing/unreadable
"""

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

KB_ROOT = Path.home() / ".hermes/kb/inexbot-open"
INDEX = KB_ROOT / "index.json"
MD_DIR = KB_ROOT / "md"
BASE_URL = "https://open.inexbot.com"
UA = {"User-Agent": "Mozilla/5.0"}
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{7,}")


def slugify(text: str) -> str:
    """MUST match crawler.py:53 exactly, or every lookup misses."""
    return re.sub(r'[<>:"|?*]', '', text.strip().replace("/", "-").replace("\\", "-"))


def fetch(path: str, timeout: int = 30) -> str | None:
    req = urllib.request.Request(BASE_URL + quote(path), headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore")
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--term", help="also report pages whose CACHE mentions this token")
    args = ap.parse_args()

    if not INDEX.exists():
        print(f"[FAIL] index.json missing at {INDEX}")
        return 2
    idx = json.loads(INDEX.read_text(encoding="utf-8"))

    if args.term:
        hits = [p for p, v in idx.items() if args.term in json.dumps(v, ensure_ascii=False)]
        print(f"index entries mentioning {args.term!r}: {len(hits)}")
        for p in sorted(hits):
            md = MD_DIR / f"{slugify(p.lstrip('/'))}.md"
            stale_tag = "  <-- INVALIDATE" if md.exists() else "  (section entry, no page)"
            print(f"  {p}{stale_tag}")
        return 1 if hits else 0

    paths = [p for p in idx if p.count("/") >= 4 and not p.endswith("/")]
    random.seed(args.seed)
    sample = random.sample(paths, min(args.sample, len(paths)))

    checked = stale_pages = total_terms = 0
    print(f"sampling {len(sample)} of {len(paths)} index paths "
          f"(seed={args.seed})\n")
    print(f"{'loc':4} {'cache-only':>11}  detail")
    for p in sample:
        loc = p.strip("/").split("/")[0]
        md = MD_DIR / f"{slugify(p.lstrip('/'))}.md"
        if not md.exists():
            continue
        live = fetch(p)
        if live is None:
            print(f"{loc:4} {'--fetch failed--':>11}")
            continue
        checked += 1
        live_tok = set(TOKEN_RE.findall(live))
        cach_tok = set(TOKEN_RE.findall(md.read_text(encoding="utf-8")))
        missing = cach_tok - live_tok
        total_terms += len(missing)
        if missing:
            stale_pages += 1
        ex = ", ".join(sorted(missing)[:3])
        print(f"{loc:4} {len(missing):>11}  {ex}")
        time.sleep(0.4)

    print(f"\nchecked {checked}; pages with cache-only terms: {stale_pages}; "
          f"total: {total_terms}")
    if stale_pages:
        print("Stale pages found. Invalidate the matching md/raw files "
              "(rename to .stale-bak) then re-run the incremental crawler. "
              "See SKILL.md -> '增量爬取的盲区'.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())