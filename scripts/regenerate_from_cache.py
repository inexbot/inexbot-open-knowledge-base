#!/usr/bin/env python3
"""Regenerate md/ and index.json from the cached raw/ HTML — no network.

WHY THIS EXISTS
---------------
The crawler is incremental: it reuses `raw/<slug>.html` + `md/<slug>.md` whenever
both exist, and only re-fetches when a URL is new.  So if you change the
*extraction* logic in crawler.py (not the fetching logic), the existing md/
files keep the OLD, buggy extraction forever — a `--force` re-crawl of 799 pages
would fix it but wastes 3 minutes and hammers upstream for nothing.

The raw/ cache is the pristine upstream HTML.  This script re-runs
`crawler.extract_content()` over the cached raw/ and rewrites md/ + index.json
locally.  Zero network traffic.

USAGE
-----
    python3 scripts/regenerate_from_cache.py            # regen md/ + index.json
    python3 scripts/regenerate_from_cache.py --check    # dry run: report only
    python3 scripts/regenerate_from_cache.py --md-only  # skip index rebuild

WHY --check FIRST
------------------
Run with --check first and read the numbers.  A second run must report
`rewritten=0 unchanged=N` — that proves extraction is deterministic and that
your fix landed.  If rewritten is still large on the second run, extraction is
NOT deterministic and something else is wrong (usually a timestamp or a
set-ordering bug); do NOT write to disk in that state.

NOTES
-----
- Writes to ~/.hermes/kb/inexbot-open/ (outside the skill repo).
- Backs up index.json to index.json.bak-<ts> before overwriting.
- Does NOT touch the proxy; the proxy reads md/ by index path, so it picks up
  the corrected content on its next 5h reload (or after a systemctl restart).
"""

import argparse
import datetime
import importlib.util
import json
import shutil
import sys
from pathlib import Path

KB_ROOT = Path.home() / ".hermes" / "kb" / "inexbot-open"
SKILL_ROOT = Path(__file__).resolve().parent.parent
CRAWLER_PY = SKILL_ROOT / "scripts" / "crawler.py"
BASE_URL = "https://open.inexbot.com"


def load_crawler():
    spec = importlib.util.spec_from_file_location("crawler", CRAWLER_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_md(crawler, pd):
    """Reproduce crawler.crawl()'s md file format EXACTLY."""
    out = f"# {pd['title']}\n\n"
    if pd["description"]:
        out += f">{pd['description']}\n\n"
    out += pd["content_md"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="dry run: report what would change, write nothing")
    ap.add_argument("--md-only", action="store_true",
                    help="regenerate md/ but leave index.json alone")
    args = ap.parse_args()

    crawler = load_crawler()
    index_f = KB_ROOT / "index.json"
    if not index_f.exists():
        print(f"[FAIL] {index_f} not found")
        return 2
    idx = json.loads(index_f.read_text(encoding="utf-8"))

    rewritten = unchanged = skipped = 0
    changed = []
    for p in sorted(idx):
        slug = crawler.slugify(p.lstrip("/"))
        raw = KB_ROOT / "raw" / f"{slug}.html"
        md = KB_ROOT / "md" / f"{slug}.md"
        if not raw.exists():
            skipped += 1
            continue
        try:
            pd = crawler.extract_content(raw.read_text(encoding="utf-8"),
                                         BASE_URL + p)
        except Exception as e:
            print(f"  [ERR] {p}: {e}")
            skipped += 1
            continue
        new = render_md(crawler, pd)
        old = md.read_text(encoding="utf-8") if md.exists() else None
        if old == new:
            unchanged += 1
            continue
        rewritten += 1
        changed.append(p)
        if not args.check:
            md.write_text(new, encoding="utf-8")

    print(f"rewritten={rewritten}  unchanged={unchanged}  skipped={skipped}")
    if rewritten:
        print(f"\n=== pages that would change ({len(changed)}) ===")
        for p in changed[:40]:
            print("  ", p)
        if len(changed) > 40:
            print(f"  ... and {len(changed) - 40} more")
    if args.check:
        print("\n[CHECK MODE] nothing written")
        return 0

    if not args.md_only:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = index_f.with_suffix(f".json.bak-{stamp}")
        shutil.copy2(index_f, bak)
        print(f"\nindex.json backed up -> {bak.name}")
        pages = []
        for p in sorted(idx):
            slug = crawler.slugify(p.lstrip("/"))
            raw = KB_ROOT / "raw" / f"{slug}.html"
            if not raw.exists():
                continue
            pd = crawler.extract_content(raw.read_text(encoding="utf-8"),
                                         BASE_URL + p)
            pd["path"] = p
            pages.append(pd)
        new_index = crawler.build_search_index(pages)
        crawler.save_json(new_index, crawler.INDEX_F)
        print(f"index rebuilt: {len(new_index)} entries")

    print("\nNext: re-run this script WITHOUT --check; it must report "
          "rewritten=0 (extraction is deterministic and the fix landed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
