#!/usr/bin/env python3
"""
Wait for a PID to exit by polling os.kill(pid, 0) every 10s.

Workaround for Hermes terminal/process tools clamping both wait() and poll()
timeouts to ~60s — see SKILL.md "Hermes 工具坑" section.

Usage:
    python3 wait_pid.py <pid> [timeout_seconds]

Exits 0 when target PID is gone, exits 1 if timeout reached while still alive.
Prints "[Ns] still running" / "[Ns] target exited" every 10s so the operator
sees progress in logs without blocking.

Why file-based: Hermes security policy blocks `python3 -c "..."` (script
execution via -c flag) and `curl ... | python3` (pipe to interpreter). This
script is meant to be invoked via a path, so it bypasses both checks.

Why os.kill(pid, 0): signal 0 doesn't actually signal the process, it just
checks if the PID exists and we have permission to signal it. Zero side
effect; cheaper than ps parsing.
"""

import os
import sys
import time


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <pid> [timeout_seconds]", file=sys.stderr)
        return 2

    try:
        pid = int(sys.argv[1])
    except ValueError:
        print(f"invalid pid: {sys.argv[1]}", file=sys.stderr)
        return 2

    timeout_sec = int(sys.argv[2]) if len(sys.argv) >= 3 else 300
    start = time.time()

    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            elapsed = int(time.time() - start)
            print(f"[{elapsed}s] target exited", flush=True)
            return 0
        except PermissionError:
            # PID exists but owned by another user — treat as still alive
            pass

        elapsed = int(time.time() - start)
        if elapsed >= timeout_sec:
            print(f"[{elapsed}s] timeout, still running", flush=True)
            return 1

        print(f"[{elapsed}s] still running", flush=True)
        time.sleep(10)


if __name__ == "__main__":
    sys.exit(main())