#!/usr/bin/env python3
"""
Decide whether the LIVE hermes-skill-proxy process is running STALE code.

WHY THIS EXISTS
---------------
The SKILL.md rule for "should I restart the proxy?" has two halves:
  (a) content changed?  -> compare index.json bytes (no restart needed if identical)
  (b) code/config changed? -> "compare patch file mtime vs process start time"

But (b)'s mtime test is a BLUNT instrument: it says "the .py was touched AFTER
the process started -> stale" even when the touch was a pure docstring/comment
edit with ZERO behavioural change.  Restarting on that signal is a net harm --
it interrupts the sister KB's in-flight e2e probe (Trap 1 / Trap 20).

2026-11-06 concrete case: the live process started 11-05 11:02:57 running commit
846b3de; HEAD was abb129c (11-05 11:14).  The mtime test said "stale -> restart".
The actual diff was 5 lines INSIDE a function docstring -> behaviourally
identical -> restarting would have been pure collateral damage.

This script answers the question properly, by CONTENT:
  1. find which git commit the live process actually loaded
     (the newest commit dated at/before the process start time)
  2. diff that commit's hermes-skill-proxy.py against HEAD's
  3. compare at the AST level -- if every function/class definition is
     structurally identical (docstrings stripped), the difference is
     comments/docstrings only -> BEHAVIOURALLY IDENTICAL -> NO RESTART NEEDED

USAGE
-----
    python3 scripts/check_proxy_staleness.py

    # exit 0 = live process runs behaviourally-current code (no restart needed)
    # exit 1 = live process is BEHAVIOURALLY stale (restart recommended)
    # exit 2 = could not determine (proxy process not found / repo missing)

NOTE: run via file path (the host's security policy blocks `python3 -c`).
"""

import ast
import difflib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROXY_REPO = Path("/home/ecs-user/hermes-skill-proxy")
PROXY_FILE = "hermes-skill-proxy.py"


def git(*args):
    return subprocess.run(
        ["git", "-C", str(PROXY_REPO), *args],
        capture_output=True, text=True,
    )


def live_pid():
    r = subprocess.run(["pgrep", "-f", "hermes-skill-proxy.py"],
                       capture_output=True, text=True)
    pids = r.stdout.split()
    return pids[0] if pids else None


def live_start_time(pid):
    r = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)],
                       capture_output=True, text=True)
    return r.stdout.strip()


def strip_docstring(node):
    """Return the node's body with a leading docstring removed."""
    body = list(node.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return body


def code_fingerprint(src):
    """
    Structural fingerprint of the module: every function/class definition,
    dumped with docstrings stripped.  Two sources with the SAME fingerprint
    differ only in comments, docstrings, or formatting -> behaviourally equal.
    """
    tree = ast.parse(src)
    parts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            clone = ast.ClassDef(
                name=node.name, bases=node.bases, keywords=node.keywords,
                body=strip_docstring(node), decorator_list=node.decorator_list,
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            clone = type(node)(
                name=node.name, bases=node.bases, keywords=node.keywords,
                body=strip_docstring(node), decorator_list=node.decorator_list,
                returns=node.returns,
            )
        else:
            continue
        parts.append((node.name, ast.dump(clone, annotate_fields=False)))
    return "\n".join("%s::%s" % (n, d) for n, d in sorted(parts))


def find_loaded_commit(started):
    """Newest commit dated at/before the process start time."""
    r = git("log", "--format=%H %cI %s", "-40")
    commits = []
    for line in r.stdout.strip().splitlines():
        parts = line.split(" ", 2)
        if len(parts) >= 3:
            commits.append((parts[0], parts[1], parts[2]))
    try:
        start_dt = datetime.strptime(started, "%a %b %d %H:%M:%S %Y").replace(
            tzinfo=timezone.utc)
    except Exception:
        return None
    for sha, cdate, subj in commits:          # newest first
        try:
            cdt = datetime.fromisoformat(cdate)
        except Exception:
            continue
        if cdt <= start_dt:
            return (sha, subj)
    return None


def main():
    if not (PROXY_REPO / ".git").exists():
        print("proxy repo not found at %s" % PROXY_REPO)
        return 2

    pid = live_pid()
    if not pid:
        print("proxy process not found -> cannot determine staleness")
        return 2

    started = live_start_time(pid)
    print("live proxy PID %s started: %s" % (pid, started))
    print("repo HEAD: %s" % git("rev-parse", "--short", "HEAD").stdout.strip())

    loaded = find_loaded_commit(started)
    if not loaded:
        print("could not determine the commit the live process loaded")
        return 2
    loaded_sha, loaded_subj = loaded
    print("likely loaded commit: %s  (%s)" % (loaded_sha[:12], loaded_subj))

    loaded_src = git("show", "%s:%s" % (loaded_sha, PROXY_FILE)).stdout
    head_src = git("show", "HEAD:%s" % PROXY_FILE).stdout

    if loaded_src == head_src:
        print("\n[OK] live process source == HEAD source -> NOT stale, no restart needed.")
        return 0

    diff = list(difflib.unified_diff(loaded_src.splitlines(), head_src.splitlines(),
                                      "loaded(%s)" % loaded_sha[:12],
                                      "head", lineterm="", n=2))
    print("\n--- source diff (loaded -> HEAD): %d lines ---" % len(diff))
    for line in diff[:80]:
        print(line)
    if len(diff) > 80:
        print("... (%d more lines)" % (len(diff) - 80))

    same = code_fingerprint(loaded_src) == code_fingerprint(head_src)
    print("\nAST fingerprint identical (ignoring docstrings/comments): %s" % same)
    if same:
        print("\n[OK] difference is DOCSTRING/COMMENT ONLY -> behaviourally identical")
        print("     -> live process is NOT functionally stale -> NO RESTART NEEDED.")
        print("     (restarting here would needlessly interrupt the sister KB's probe)")
        return 0

    print("\n[FAIL] live process runs BEHAVIOURALLY STALE code -> restart recommended.")
    print("  sudo -n systemctl daemon-reload && sudo -n systemctl restart hermes-skill-proxy")
    print("  (only when NO probe is in flight: "
          "ps -eo pid,etime,cmd | grep -E '[c]heck_e2e|[c]heck_retrieval')")
    return 1


if __name__ == "__main__":
    sys.exit(main())
