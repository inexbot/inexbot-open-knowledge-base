#!/usr/bin/env python3
"""Regression test for check_proxy_health.py's floor/target logic.

A health check that can never FAIL is worse than no check at all.
SKILL.md trap 47 ("an audit script that is permanently red is more dangerous
than no script -- a wrong criterion reports FAIL every time and buries real
faults") has a mirror case: a permanently-GREEN check that never reports
anything is just as useless.  So the criterion must be verified against
synthetic cases in BOTH directions.

The distinction being tested (2026-11-27):
  The proxy serves the LAST KNOWN-GOOD index in memory until its 5h auto
  reload picks up a newer on-disk one.  After a growth crawl the proxy
  legitimately reports the OLD count for up to 5 hours.  That must NOT be
  reported as a fault.  But a genuine drop below the floor MUST be.

Cases:
  1. growth + proxy not yet reloaded (memory == floor < disk)  -> exit 0
  2. healthy (memory == disk == floor)                           -> exit 0
  3. proxy ahead of disk (memory > disk)                         -> exit 0
  4. genuine regression: memory < floor AND < disk              -> exit 1
  5. loaded=False                                                -> exit 1

Run:
  /usr/bin/python3 scripts/test_proxy_health_regression.py
"""
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent / "check_proxy_health.py"

spec = importlib.util.spec_from_file_location("cph", SCRIPT)
cph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cph)

CASES = [
    # name, payload, disk_counts, expected_exit
    ("growth, proxy not yet reloaded", {
        "status": "ok", "indexes": {"inexbot-open": {"docs": 832, "loaded": True},
                                     "inexbot": {"docs": 562, "loaded": True}}},
     {"inexbot-open": 944, "inexbot": 562}, 0),
    ("healthy", {
        "status": "ok", "indexes": {"inexbot-open": {"docs": 944, "loaded": True},
                                     "inexbot": {"docs": 562, "loaded": True}}},
     {"inexbot-open": 944, "inexbot": 562}, 0),
    ("proxy ahead of disk", {
        "status": "ok", "indexes": {"inexbot-open": {"docs": 999, "loaded": True},
                                     "inexbot": {"docs": 562, "loaded": True}}},
     {"inexbot-open": 944, "inexbot": 562}, 0),
    ("genuine regression (below floor and disk)", {
        "status": "ok", "indexes": {"inexbot-open": {"docs": 100, "loaded": True},
                                     "inexbot": {"docs": 562, "loaded": True}}},
     {"inexbot-open": 944, "inexbot": 562}, 1),
    ("loaded=False", {
        "status": "ok", "indexes": {"inexbot-open": {"docs": 944, "loaded": False},
                                     "inexbot": {"docs": 562, "loaded": True}}},
     {"inexbot-open": 944, "inexbot": 562}, 1),
]


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def run_case(payload, disk):
    with mock.patch.object(cph.urllib.request, "urlopen", lambda *a, **k: FakeResp(payload)), \
         mock.patch.object(cph, "disk_docs", lambda name: disk.get(name)):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            code = cph.main()
        return code, buf.getvalue()


ok = True
for name, payload, disk, expected in CASES:
    code, out = run_case(payload, disk)
    good = code == expected
    ok = ok and good
    print(f"  [{'OK' if good else 'FAIL'}] {name}: exit={code} (expected {expected})")
    if not good:
        print(out)

print()
print("PASS: floor/target logic detects regressions" if ok else "FAIL: false green / false red")
sys.exit(0 if ok else 1)
