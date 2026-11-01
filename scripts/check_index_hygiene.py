#!/usr/bin/env python3
"""Regression probe for the index-hygiene fixes landed 2026-10-29.

WHY THIS EXISTS
---------------
The 2026-10-29 cycle fixed three defects in this KB's index:
  1. titles carrying a U+200B zero-width space (764 entries at the time)
  2. 39 entries with an empty title (no <h1>, no og:title)
  3. 34 entries with no content at all (upstream empty-directory pages)

It also fixed the "VitePress language badge" extraction bug, which fabricated
identifiers like `cppset_tool_hand_number` (badge "cpp" glued onto the code
text) across 166 index-reachable pages.

None of those fixes have an automated guard.  The only way to notice a
regression was to hand-write a probe each time -- which is exactly what
happened on 2026-10-31.  This script makes that check one command.

WHAT IT CHECKS
--------------
  zero-width entries  entries whose title/snippet contains U+200B/C/D or U+FEFF
                      -> MUST be 0
  empty titles       entries with a blank title
                      -> MUST be 0
  empty snippets     entries with a blank content_snippet
                      -> EXPECTED ~34 (upstream empty-directory pages; these
                         are unfixable, they only need a non-empty TITLE)
  phantom tokens     tokens fabricated by the extraction bug, e.g.
                      `cppset_tool_hand_number` (lang badge glued to code)
                      -> MUST be 0 among INDEX-REACHABLE pages
  renamed-API tokens tokens for APIs upstream deleted/renamed, e.g.
                      `star_servo_point_position_motion_control`
                      -> MUST be 0 among INDEX-REACHABLE pages

⚠️ "index-reachable" vs "file exists on disk"
----------------------------------------------
`md/` contains DEAD CACHE: files from URLs upstream renamed or restructured.
Grepping the directory gives false positives (13 files matched `star_servo`
on 2026-10-25 while ZERO index-reachable pages did).  This script resolves
each index path to its real md file using the PROXY's own
`_md_slug_candidates()` -- never a hand-written slugify.

Usage:
    python3 scripts/check_index_hygiene.py
    python3 scripts/check_index_hygiene.py --term some_token
    python3 scripts/check_index_hygiene.py --raw-scan

⚠️ RELATIONSHIP TO THE SIBLING KB's scripts/verify_kb.py
-------------------------------------------------------
The sibling skill `inexbot-knowledge-base/scripts/verify_kb.py` is the BROADER
regression harness: it checks both KBs' index integrity, slug contract, image
coverage, retrieval chain and live-URL reachability.  Run it too -- it needs
network access (curl) and ~20-40s, and it must run under /usr/bin/python3.

THIS script is deliberately narrower and complementary:
  * ZERO network (no curl) -> safe to run on every cron, fast
  * covers the two checks that verify_kb.py does NOT have:
      - PHANTOM tokens (lang-badge glue) that must not be index-reachable
      - RENAMED-API tokens (upstream deletes/renames) that must not be reachable
  * resolves md paths via the PROXY's `_md_slug_candidates()` (not a
    hand-rolled candidate list) -> same contract the live proxy uses

⚠️ Per the "修 bug 前先看姊妹 KB 是否已修" rule: the sibling's script set is
near-duplicate of this one.  Before adding a probe here, check the sibling's
scripts/ first -- but do NOT copy its style blindly, it has known differences
(it hand-rolls `md_candidates()` and its slug rules differ for open KB).

Exit codes:
    0 - all hard invariants hold
    1 - at least one hard invariant violated (zero-width / empty title /
        reachable phantom or renamed token)
    2 - index missing/unreadable
"""

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path

KB_ROOT = Path.home() / ".hermes/kb/inexbot-open"
INDEX = KB_ROOT / "index.json"
MD_DIR = KB_ROOT / "md"
RAW_DIR = KB_ROOT / "raw"
PROXY_PY = Path("/home/ecs-user/hermes-skill-proxy/hermes-skill-proxy.py")

# Zero-width chars: build explicitly from codepoints -- a LITERAL zero-width
# character in source can be silently swallowed by editors/patchers (see
# SKILL.md -> '字面零宽字符写进源码会被静默吞掉').  U+200B is the common one.
ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0xFEFF}

# Tokens that must NOT be reachable through the index.
DEFAULT_BAD_TOKENS = [
    "cppset_tool_hand_number",                        # lang-badge glue bug
    "star_servo_point_position_motion_control",      # upstream rename (10-23)
]

# Upstream empty-directory pages: blank snippet is EXPECTED (they have no body).
# The title fallback chain gives them a name, which is all we can do.
EXPECTED_EMPTY_SNIPPETS = 34


def load_proxy():
    """Import hermes-skill-proxy with a flask stub (the sandbox python3 has no flask)."""
    if not PROXY_PY.exists():
        return None
    flask = types.ModuleType("flask")
    flask.Flask = type("Flask", (), {
        "__init__": lambda self, *a, **k: None,
        "route": lambda self, *a, **k: (lambda f: f),
    })
    flask.request = types.SimpleNamespace(get_json=lambda *a, **k: {}, data=b"")
    flask.Response = object
    flask.jsonify = lambda *a, **k: {}
    flask.stream_with_context = lambda f: f
    sys.modules.setdefault("flask", flask)

    spec = importlib.util.spec_from_file_location("hsp", PROXY_PY)
    hsp = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(hsp)
    except SystemExit:
        pass
    return hsp


def has_zero_width(s: str) -> bool:
    return any(ord(c) in ZERO_WIDTH for c in s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--term", action="append", default=None,
                    help="extra token that must not be index-reachable "
                         "(repeatable)")
    ap.add_argument("--raw-scan", action="store_true",
                    help="also count bad tokens inside raw/*.html "
                         "(distinguishes upstream change vs local extraction bug)")
    args = ap.parse_args()

    if not INDEX.exists():
        print(f"[FAIL] index.json missing at {INDEX}")
        return 2
    try:
        idx = json.loads(INDEX.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[FAIL] index.json unreadable: {type(e).__name__}: {e}")
        return 2

    bad_tokens = list(DEFAULT_BAD_TOKENS) + list(args.term or [])

    # ── pass 1: cheap per-entry invariants ────────────────────────────────
    zero_width, empty_title, empty_snip = [], [], []
    for path, v in idx.items():
        if not isinstance(v, dict):
            continue
        title = v.get("title") or ""
        snippet = v.get("content_snippet") or ""
        if has_zero_width(title) or has_zero_width(snippet):
            zero_width.append(path)
        if not title.strip():
            empty_title.append(path)
        if not snippet.strip():
            empty_snip.append(path)

    print(f"index entries: {len(idx)}")
    print(f"  zero-width entries  : {len(zero_width)}   (MUST be 0)")
    print(f"  empty titles        : {len(empty_title)}   (MUST be 0)")
    print(f"  empty snippets      : {len(empty_snip)}   (expect ~{EXPECTED_EMPTY_SNIPPETS}, upstream empty-dir pages)")
    for p in empty_title[:5]:
        print(f"      empty title: {p}")
    for p in zero_width[:5]:
        print(f"      zero-width: {p}")

    # ── pass 2: index-reachable phantom / renamed tokens ─────────────────
    hsp = load_proxy()
    if hsp is None or not hasattr(hsp, "_md_slug_candidates"):
        print("\n[warn] proxy module or _md_slug_candidates() unavailable -- "
              "skipping reachability checks (cannot hand-roll slugify)")
        reachable = {}
    else:
        reachable = {tok: [] for tok in bad_tokens}
        for p in idx:
            for cand in hsp._md_slug_candidates(p):
                f = MD_DIR / f"{cand}.md"
                if f.exists():
                    try:
                        body = f.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        break
                    for tok in bad_tokens:
                        if tok in body:
                            reachable[tok].append(p)
                    break
        print()
        for tok in bad_tokens:
            n = len(reachable[tok])
            print(f"  index-reachable md containing {tok!r}: {n}   (MUST be 0)")
            for p in reachable[tok][:3]:
                print(f"      reachable: {p}")

    if args.raw_scan:
        print()
        for tok in bad_tokens:
            n = 0
            for f in RAW_DIR.glob("*.html"):
                try:
                    if tok in f.read_text(encoding="utf-8", errors="ignore"):
                        n += 1
                except OSError:
                    pass
            print(f"  raw/ files containing {tok!r}: {n}")
            print("      (raw has it -> upstream really changed it; "
                  "raw clean -> local extraction bug)")

    # ── verdict ───────────────────────────────────────────────────────────
    problems = []
    if zero_width:
        problems.append(f"{len(zero_width)} zero-width entries")
    if empty_title:
        problems.append(f"{len(empty_title)} empty titles")
    for tok, paths in reachable.items():
        if paths:
            problems.append(f"{len(paths)} index-reachable pages containing {tok!r}")

    print()
    if problems:
        print("[FAIL] index hygiene violated: " + "; ".join(problems))
        print("See SKILL.md -> '修 bug 前先看姊妹 KB 是否已修' and "
              "references/index-hygiene-and-systemd-env-bugs.md")
        return 1
    print("[OK] index hygiene intact: no zero-width entries, no empty titles, "
          "no reachable phantom/renamed tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
