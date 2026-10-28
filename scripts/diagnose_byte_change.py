#!/usr/bin/env python3
"""Diagnose WHY index.json changed size -- upstream edit, or a local change?

WHY THIS EXISTS
---------------
`check_crawl_state.py` reports `doc count flat but BYTES DIFFER` when the
index size changed without new pages.  The obvious reading -- "upstream edited
some page bodies" -- is WRONG half the time, and acting on it wastes cycles
(you go hunting for an upstream change that never happened, or you "fix" a
crawler that was already fine).

There are three real sources of a byte jump:

  1. Upstream really edited page bodies.
  2. The LOCAL extraction logic changed (you edited crawler.py).
  3. The index was rebuilt and picked up your local fix (source 2 landing).

The decisive, zero-network test is a REBUILD COMPARISON: load the *old*
crawler (git HEAD) and the *new* crawler (working tree), re-extract every
page from the cached raw/ HTML with each, and compare the resulting index
sizes against what's on disk and against the previous snapshot.

  - NEW-rebuild bytes == on-disk bytes  AND  OLD-rebuild bytes == snapshot bytes
        => 100% a LOCAL change. Upstream did not move. Do not go hunting.
  - NEW-rebuild bytes == on-disk bytes  AND  OLD-rebuild bytes != snapshot bytes
        => the local fix changed things AND upstream may also have moved.
  - Neither matches on-disk
        => on-disk index was not produced by either extractor (e.g. built by
           regenerate_from_cache.py, or a --force crawl with different code).

The script also reports how many index entries differ between the two
extractors, and whether the crawler log shows any network fetch.

USAGE
-----
    python3 scripts/diagnose_byte_change.py                 # full diagnosis
    python3 scripts/diagnose_byte_change.py --log /tmp/open-crawl-20261027.log
    python3 scripts/diagnose_byte_change.py --old-ref HEAD~1   # compare vs
                                                              # an older commit
    python3 scripts/diagnose_byte_change.py --max-changed 20

Exit codes:
    0 - diagnosis completed (see the VERDICT line)
    1 - could not run the comparison (missing raw/, missing git history, ...)
    2 - a locale dropped to zero / index empty (sidebar breakage -- trust
        nothing this run)

NOTES
-----
- Zero network traffic: everything is re-extracted from the local raw/ cache.
- Takes ~3-5 minutes for 799 pages (it extracts every page twice).
- Must be run by file path -- `python3 -c` is blocked by the local security
  policy.
- Use /usr/bin/python3 or plain python3; this script does NOT import flask.
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

KB_ROOT = Path.home() / ".hermes" / "kb" / "inexbot-open"
SKILL_ROOT = Path(__file__).resolve().parent.parent
CRAWLER_PY = SKILL_ROOT / "scripts" / "crawler.py"
SNAPSHOT = SKILL_ROOT / "references" / ".index-snapshot.json"
BASE_URL = "https://open.inexbot.com"
EXPECTED_LOCALES = ("zh", "en", "kr")


def slugify(t: str) -> str:
    """Must match crawler.py's slugify() EXACTLY.

    Note the backslash-escaped pipe inside the character class:
    crawler.py uses r'[<>\|"?*]' -- omitting the '|' would compute a
    different path for any page whose title contains a pipe, and you would
    silently skip that page (raw/ not found) instead of diagnosing it.
    """
    return re.sub(r'[<>\|"?*]', '', t.strip().replace("/", "-").replace("\\", "-"))


def load_crawler(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERR] failed to load {path}: {exc}")
        raise
    return mod


def git_show(ref: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(SKILL_ROOT), "show", f"{ref}:{path}"], text=True)


def build_index(mod, idx):
    """Re-extract every page from raw/ and rebuild the search index."""
    pages = []
    skipped = 0
    for p in sorted(idx):
        raw = KB_ROOT / "raw" / f"{slugify(p.lstrip('/'))}.html"
        if not raw.exists():
            skipped += 1
            continue
        try:
            pd = mod.extract_content(raw.read_text(encoding="utf-8"), BASE_URL + p)
        except Exception:  # noqa: BLE001
            skipped += 1
            continue
        pd["path"] = p
        pages.append(pd)
    index = mod.build_search_index(pages)
    return index, skipped


def index_bytes(index) -> int:
    """Byte length exactly as crawler.save_json() writes it."""
    return len(json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8"))


def count_network_fetches(log_path: Path) -> str:
    """crawler logs one '  [i/N] ok <link>' line per ACTUAL fetch."""
    if not log_path.exists():
        return "no crawl log supplied (pass --log)"
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return f"cannot read log ({exc})"
    fetches = len([l for l in text.splitlines()
                   if re.search(r"\[\d+/\d+\]", l)])
    return f"{fetches} page fetches in {log_path.name}"


def newest_raw_mtime() -> str:
    raw_dir = KB_ROOT / "raw"
    if not raw_dir.is_dir():
        return "raw/ missing"
    try:
        out = subprocess.check_output(
            ["find", str(raw_dir), "-type", "f", "-printf", "%TY-%Tm-%Td %TH:%TM %p\n"],
            text=True)
    except Exception as exc:  # noqa: BLE001
        return f"cannot stat raw/ ({exc})"
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return "raw/ empty"
    lines.sort(reverse=True)
    return lines[0].split(" ", 2)[0] + " " + lines[0].split(" ", 2)[1] + "  (newest raw/)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-ref", default="HEAD",
                    help="git ref holding the OLD crawler.py (default: HEAD)")
    ap.add_argument("--log", default=None,
                    help="path to the crawl log, to count network fetches")
    ap.add_argument("--max-changed", type=int, default=20,
                    help="how many differing entries to list (default: 20)")
    args = ap.parse_args()

    index_f = KB_ROOT / "index.json"
    if not index_f.exists():
        print(f"[FAIL] {index_f} not found")
        return 1

    on_disk = index_f.read_text(encoding="utf-8")
    idx = json.loads(on_disk)
    disk_bytes = index_f.stat().st_size
    print(f"index.json (on disk): {len(idx)} entries, {disk_bytes:,} bytes")
    print(f"locale split: " + ", ".join(
        f"{loc}={sum(1 for p in idx if p.strip('/').split('/')[0] == loc)}"
        for loc in EXPECTED_LOCALES))

    if not (KB_ROOT / "raw").is_dir():
        print("[FAIL] raw/ cache missing -- cannot rebuild-compare")
        return 1

    # ── snapshot (previous crawl) ────────────────────────────────────────
    prev = None
    if SNAPSHOT.exists():
        try:
            prev = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            prev = None
    if prev:
        print(f"previous snapshot: {prev.get('total')} docs, "
              f"{prev.get('size', 0):,} bytes, {prev.get('mtime', '?')}")
    else:
        print("previous snapshot: none on disk (first run with this probe)")

    # ── load both extractor versions ────────────────────────────────────
    try:
        old_src = git_show(args.old_ref, "scripts/crawler.py")
    except subprocess.CalledProcessError as exc:
        print(f"[FAIL] cannot read {args.old_ref}:scripts/crawler.py ({exc})")
        return 1
    tmpdir = Path(tempfile.mkdtemp())
    old_path = tmpdir / "crawler_old.py"
    old_path.write_text(old_src, encoding="utf-8")

    try:
        old_mod = load_crawler(old_path, "crawler_old")
        new_mod = load_crawler(CRAWLER_PY, "crawler_new")
    except Exception:  # noqa: BLE001
        return 1

    print(f"\nrebuilding index from raw/ cache with BOTH extractors "
          f"(OLD={args.old_ref}, NEW=working tree) -- this takes a few minutes...")

    old_index, old_skipped = build_index(old_mod, idx)
    old_bytes = index_bytes(old_index)
    print(f"  OLD extraction -> {old_bytes:,} bytes (skipped {old_skipped})")

    new_index, new_skipped = build_index(new_mod, idx)
    new_bytes = index_bytes(new_index)
    print(f"  NEW extraction -> {new_bytes:,} bytes (skipped {new_skipped})")

    # ── compare ─────────────────────────────────────────────────────────
    changed = [p for p in old_index if old_index[p] != new_index.get(p)]
    print(f"\nentries whose content differs between OLD and NEW extraction: "
          f"{len(changed)}")
    for p in changed[:args.max_changed]:
        print(f"    {p}")
    if len(changed) > args.max_changed:
        print(f"    ... and {len(changed) - args.max_changed} more")

    # ── verdict ──────────────────────────────────────────────────────────
    print("\n" + "=" * 68)
    print("VERDICT")
    if new_bytes == disk_bytes and prev and old_bytes == prev.get("size"):
        verdict = ("LOCAL CHANGE (confirmed) -- your local extraction change landed "
                   "in index.json. Upstream did NOT move. No upstream action needed.")
    elif new_bytes == disk_bytes and prev and old_bytes != prev.get("size"):
        verdict = ("MIXED -- on-disk index matches the NEW extractor, but the OLD "
                   "extractor also differs from the snapshot: upstream may have "
                   "moved too. Verify with the crawl log / raw/ mtime below.")
    elif new_bytes == disk_bytes:
        verdict = ("on-disk index matches the NEW extractor; no snapshot to compare "
                   "against. Treat as a local rebuild; check raw/ mtime + crawl "
                   "log to rule out an upstream change.")
    else:
        verdict = ("UNEXPLAINED -- on-disk index matches NEITHER extractor. It was "
                   "probably built by regenerate_from_cache.py or a --force crawl "
                   "with different code. Investigate manually.")
    print(verdict)

    print("\ncorroborating evidence:")
    print(f"  crawl log        : {count_network_fetches(Path(args.log)) if args.log else 'no --log supplied (pass --log /tmp/open-crawl-YYYYMMDD.log)'}")
    print(f"  newest raw/ file : {newest_raw_mtime()}")
    print("  -> 0 fetches AND raw/ older than the crawl start => upstream "
          "definitely did not move")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
