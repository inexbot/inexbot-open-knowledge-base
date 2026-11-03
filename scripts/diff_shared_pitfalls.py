#!/usr/bin/env python3
"""
Diff the two KB copies of references/shared-proxy-service-pitfalls.md.

WHY THIS EXISTS
---------------
The two KB skills (inexbot-knowledge-base / inexbot-open-knowledge-base) each
keep a copy of references/shared-proxy-service-pitfalls.md, and both crons run
in the SAME 11:00 window -- so BOTH write that file.  The long-standing rule
was "sister's copy is authoritative -> cp over yours".  That rule was
DISPROVEN on 2026-11-02: this KB's copy was 441 lines / 21,204 B while the
sister's was 393 lines / 18,586 B -- THIS KB's copy was the SUPERSET (it
already contained Trap 14, which the sister had not yet back-written).
A blind `cp` would have silently destroyed Trap 14.

So: always diff FIRST, then decide between overwrite / merge / reverse-patch.

USAGE
-----
    python3 scripts/diff_shared_pitfalls.py

    # exit 0 = identical, exit 1 = they differ (inspect the diff)
    # exit 2 = one of the files is missing

The script prints, for each side, the line count / byte count / sha1, the
number of "## 陷阱 N" sections, and a unified diff of sister -> ours.

NOTE: run via file path (the host's security policy blocks `python3 -c`).
"""

import difflib
import hashlib
import re
import sys
from pathlib import Path

HOME = Path.home()
KB_DIRS = {
    "sister": HOME / ".hermes/skills/productivity/inexbot-knowledge-base",
    "ours": HOME / ".hermes/skills/productivity/inexbot-open-knowledge-base",
}
REL = Path("references/shared-proxy-service-pitfalls.md")


def section_titles(text):
    return re.findall(r"^## (陷阱 \d+[^\n]*)", text, re.M)


def sort_key(title):
    """Sort 陷阱 sections numerically (陷阱 2 before 陷阱 10), not lexically."""
    m = re.match(r"陷阱 (\d+)", title)
    return (int(m.group(1)) if m else 999, title)


def main():
    paths = {k: v / REL for k, v in KB_DIRS.items()}
    missing = [k for k, p in paths.items() if not p.exists()]
    if missing:
        print("MISSING: %s" % ", ".join("%s (%s)" % (k, paths[k]) for k in missing))
        print("  -> one KB's repo may not have been cloned yet")
        return 2

    texts = {k: p.read_text(encoding="utf-8") for k, p in paths.items()}
    lines = {k: t.splitlines() for k, t in texts.items()}

    for k in ("sister", "ours"):
        raw = paths[k].read_bytes()
        print("%-7s %5d lines  %7d bytes  sha1=%s"
              % (k, len(lines[k]), len(raw), hashlib.sha1(raw).hexdigest()))
        secs = section_titles(texts[k])
        print("        sections: %d  -> %s" % (len(secs), ", ".join(secs)))
    print()

    if texts["sister"] == texts["ours"]:
        print("IDENTICAL -- nothing to sync.")
        return 0

    s_secs = set(section_titles(texts["sister"]))
    o_secs = set(section_titles(texts["ours"]))
    only_sister = sorted(s_secs - o_secs, key=sort_key)
    only_ours = sorted(o_secs - s_secs, key=sort_key)
    if only_sister:
        print("!! ONLY IN SISTER (we are missing these -> consider adding):")
        for t in only_sister:
            print("     - %s" % t)
    if only_ours:
        print("!! ONLY IN OURS (a blind `cp` from sister would DESTROY these):")
        for t in only_ours:
            print("     - %s" % t)
    print()

    print("=" * 68)
    print("unified diff  (sister -> ours)")
    print("=" * 68)
    for line in difflib.unified_diff(lines["sister"], lines["ours"],
                                     "sister", "ours", lineterm="", n=1):
        print(line)

    print()
    print("DECISION GUIDE")
    print("  - sister has sections we lack AND we have none of our own")
    print("    -> cp sister over ours")
    print("  - we have sections sister lacks  -> DO NOT cp; reverse-patch the")
    print("    missing sister lines into ours (keep both)")
    print("  - both have distinct sections    -> hand-merge, keep BOTH")
    return 1


if __name__ == "__main__":
    sys.exit(main())
