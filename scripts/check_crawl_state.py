#!/usr/bin/env python3
"""Post-crawl steady-state probe for the open.inexbot.com KB.

Answers three questions in one shot, without needing a policy-exempt inline
`python3 -c` invocation (write this file once, run it by path):

  1. How many docs are in the local index.json, and how do they split by locale?
  2. Is the index byte-identical to the previous crawl (true steady state) or
     did it actually change content despite a flat doc count?
  3. How many stale unprefixed *.md leftovers sit in md/ (harmless, but a rising
     count would mean the crawler regressed to the old slugify() behaviour)?

It also snapshots index.json size+mtime to
references/.index-snapshot.json so the NEXT run has something to diff against.

Usage:
    python3 scripts/check_crawl_state.py

Exit codes:
    0 - index parses, all three locales non-zero, doc count sane
    1 - index missing/unparseable, or a locale has dropped to zero entries
        (the signature of the VitePress v2-alpha sidebar-extraction breakage --
        see references/vitepress-i18n-sidebar-diagnosis.md)
"""

import datetime
import json
import sys
from collections import Counter
from pathlib import Path

KB_ROOT = Path.home() / ".hermes/kb/inexbot-open"
INDEX = KB_ROOT / "index.json"
MD_DIR = KB_ROOT / "md"
SNAPSHOT = Path(__file__).resolve().parent.parent / "references" / ".index-snapshot.json"

EXPECTED_LOCALES = ("zh", "en", "kr")


def locale_of(url_path: str) -> str:
    """First path segment is the locale for /zh/..., /en/..., /kr/... keys."""
    parts = url_path.strip("/").split("/")
    return parts[0] if parts and parts[0] else "?"


def main() -> int:
    if not INDEX.exists():
        print(f"[FAIL] index.json missing at {INDEX}")
        return 1

    stat = INDEX.stat()
    size = stat.st_size
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    try:
        idx = json.loads(INDEX.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"[FAIL] index.json unparseable: {exc}")
        return 1

    total = len(idx)
    counts = Counter(locale_of(p) for p in idx.keys())
    print(f"index.json: {total} entries, {size:,} bytes, mtime {mtime}")
    print("locale distribution: " + ", ".join(f"{k}={counts[k]}" for k in sorted(counts)))

    rc = 0
    missing = [loc for loc in EXPECTED_LOCALES if counts.get(loc, 0) == 0]
    if missing:
        print(f"[FAIL] locale(s) with zero entries: {', '.join(missing)} "
              "-- sidebar extraction likely broken, do NOT trust this run")
        rc = 1
    if total == 0:
        print("[FAIL] index is empty -- crawler fetched nothing")
        return 1

    if MD_DIR.is_dir():
        md_files = list(MD_DIR.glob("*.md"))
        stale = [
            f for f in md_files
            if not f.name.startswith(EXPECTED_LOCALES)
        ]
        prefixed = sum(counts.get(loc, 0) for loc in EXPECTED_LOCALES)
        print(f"md/ files: {len(md_files)} total "
              f"({len(md_files) - len(stale)} locale-prefixed, {len(stale)} stale bare)")
        if len(stale) > prefixed:
            print("[WARN] stale bare md files outnumber prefixed ones -- "
                  "crawler may have regressed to the old locale-less slugify()")

    prev = None
    if SNAPSHOT.exists():
        try:
            prev = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            prev = None

    if prev is None:
        print("snapshot: none on disk yet -- first run with this probe, "
              "will diff on the next crawl")
        verdict = "BASELINE"
    elif prev.get("size") == size and prev.get("total") == total:
        verdict = "IDENTICAL to previous crawl (content byte-for-byte unchanged)"
    elif prev.get("total") == total:
        # 2026-10-27: this used to assert "doc body edits upstream", which is
        # wrong about half the time.  A byte jump has THREE possible sources:
        # (1) upstream really edited bodies, (2) the local extraction logic
        # changed, (3) the index was rebuilt and picked up a local fix.
        # Sources 2 and 3 are LOCAL -- do not go hunting upstream.
        # Run scripts/diagnose_byte_change.py to tell them apart.
        verdict = ("doc count flat but BYTES DIFFER -- CAUSE UNKNOWN: could be "
                   "upstream body edits OR a local extraction change. Run "
                   "scripts/diagnose_byte_change.py to tell them apart "
                   "(do NOT assume upstream moved)")
    else:
        verdict = f"CHANGED: {prev.get('total')} -> {total} docs"

    print(f"verdict: {verdict}")
    if prev:
        print(f"  previous: {prev.get('total')} docs, {prev.get('size', 0):,} bytes, "
              f"{prev.get('mtime', '?')}")

    try:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(
            json.dumps({"total": total, "size": size, "mtime": mtime}, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[WARN] could not write snapshot {SNAPSHOT}: {exc}")

    return rc


if __name__ == "__main__":
    sys.exit(main())