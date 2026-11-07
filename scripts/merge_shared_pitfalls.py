#!/usr/bin/env python3
"""
Merge the two KB copies of references/shared-proxy-service-pitfalls.md WITHOUT losing either side.

WHY THIS EXISTS
---------------
`scripts/diff_shared_pitfalls.py` DIAGNOSES the drift between the sister KB's copy
(`inexbot-knowledge-base`) and ours (`inexbot-open-knowledge-base`).  Its decision
guide ends with:

    - both have distinct sections    -> hand-merge, keep BOTH

"Hand-merge" a 39 KB file with 21 numbered sections and you WILL drop or
duplicate something -- and the failure is silent (the file still looks fine,
`git diff` just shows a confusingly large hunk).

2026-11-06 concrete case: sister 787 lines / 38,872 B vs ours 760 lines / 37,406 B.
Each side had content the other lacked:
  - sister only: Trap 11's "three-false-positive fingerprint" table,
                 Trap 17's "closed as of 2026-11-05" annotation
  - ours only:  the `check_proxy_env.py --units` guard paragraph inside Trap 20,
                 the `deployment-readiness-checklist.md` cross-reference
A blind `cp` would have destroyed our two blocks.  This script merged both in one
pass and then VERIFIED that no section was lost on either side.

ALGORITHM
----------
difflib three-way merge, with the SISTER copy as the base:
  - `equal`    -> take sister lines
  - `delete`   -> take sister lines (sister-only content is KEPT)
  - `insert`   -> take OUR lines (our-only content is RE-ADDED; a blind cp drops it)
  - `replace`  -> take sister block THEN our block (both kept)

Then verify by section header:
  - every "## ..." header present in sister must survive in the merged file
  - every "## ..." header present in ours  must survive in the merged file
exit 1 if either side lost a section.

USAGE
-----
    python3 scripts/merge_shared_pitfalls.py            # merge (writes ours)
    python3 scripts/merge_shared_pitfalls.py --check    # dry-run, no write
    python3 scripts/merge_shared_pitfalls.py --sync-sister  # also copy result to sister

    # exit 0 = merged OK, no section lost
    # exit 1 = a section was lost (DO NOT commit; inspect)
    # exit 2 = one of the files is missing

NOTE: run via file path (the host's security policy blocks `python3 -c`).
CAUTION: only run this when `diff_shared_pitfalls.py` reported DISTINCT sections
on both sides.  If one side is a strict superset, prefer the simpler reverse-patch
and do not run a merge.
"""

import difflib
import hashlib
import re
import shutil
import sys
from pathlib import Path

HOME = Path.home()
KB_DIRS = {
    "sister": HOME / ".hermes/skills/productivity/inexbot-knowledge-base",
    "ours": HOME / ".hermes/skills/productivity/inexbot-open-knowledge-base",
}
REL = Path("references/shared-proxy-service-pitfalls.md")


def sha1(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:12]


def section_headers(text: str):
    return re.findall(r"^## .*$", text, re.M)


def main() -> int:
    check_only = "--check" in sys.argv
    sync_sister = "--sync-sister" in sys.argv

    paths = {k: v / REL for k, v in KB_DIRS.items()}
    missing = [k for k, p in paths.items() if not p.exists()]
    if missing:
        print("MISSING: %s" % ", ".join("%s (%s)" % (k, paths[k]) for k in missing))
        return 2

    sister_lines = paths["sister"].read_text(encoding="utf-8").splitlines(keepends=True)
    our_lines = paths["ours"].read_text(encoding="utf-8").splitlines(keepends=True)

    if sister_lines == our_lines:
        print("IDENTICAL -- nothing to merge.")
        return 0

    sm = difflib.SequenceMatcher(None, sister_lines, our_lines, autojunk=False)
    merged = []
    our_hunks = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            merged.extend(sister_lines[i1:i2])
        elif tag == "delete":
            # sister-only content -> KEEP
            merged.extend(sister_lines[i1:i2])
        elif tag == "insert":
            # ours-only content -> RE-ADD (a blind cp would drop it)
            merged.extend(our_lines[j1:j2])
            our_hunks += 1
        elif tag == "replace":
            # mixed block -> keep BOTH, sister first
            merged.extend(sister_lines[i1:i2])
            merged.extend(our_lines[j1:j2])
            our_hunks += 1

    out = "".join(merged)
    if not out.endswith("\n"):
        out += "\n"

    s_secs = section_headers("".join(sister_lines))
    m_secs = section_headers(out)
    o_secs = section_headers("".join(our_lines))

    lost_sister = [s for s in s_secs if s not in m_secs]
    lost_ours = [s for s in o_secs if s not in m_secs]

    print("sister : %5d lines / %7d bytes / sha1=%s"
          % (len(sister_lines), paths["sister"].stat().st_size, sha1(paths["sister"])))
    print("ours   : %5d lines / %7d bytes / sha1=%s"
          % (len(our_lines), paths["ours"].stat().st_size, sha1(paths["ours"])))
    print("merged : %5d lines / %7d bytes (our-only hunks re-added: %d)"
          % (out.count("\n"), len(out.encode()), our_hunks))
    print()
    print("sister sections: %d | merged sections: %d | MISSING from merged: %d"
          % (len(s_secs), len(m_secs), len(lost_sister)))
    for s in lost_sister:
        print("  MISSING (sister):", s)
    print("our sections lost: %d" % len(lost_ours))
    for s in lost_ours:
        print("  LOST (ours):", s)

    if lost_sister or lost_ours:
        print("\n[FAIL] a section was lost -- do NOT commit. Inspect manually.")
        return 1

    if check_only:
        print("\n[CHECK MODE] no write performed.")
        return 0

    paths["ours"].write_text(out, encoding="utf-8")
    print("\n[OK] wrote %s (sha1=%s)" % (paths["ours"], sha1(paths["ours"])))

    if sync_sister:
        shutil.copy2(paths["ours"], paths["sister"])
        print("[OK] synced sister copy too (sha1=%s)" % sha1(paths["sister"]))

    print("\nNext: verify both sides, then commit:")
    print("  sha1sum ~/.hermes/skills/productivity/{inexbot,inexbot-open}-knowledge-base/references/shared-proxy-service-pitfalls.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
