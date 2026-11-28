#!/bin/bash
# Run the proxy-health floor/target regression test.
# (Kept as a shell wrapper so it can be invoked without remembering the
# /usr/bin/python3 requirement -- the sandbox python3 lacks some deps.)
set -m
exec /usr/bin/python3 /home/ecs-user/.hermes/skills/productivity/inexbot-open-knowledge-base/scripts/test_proxy_health_regression.py
