"""Claude PreToolUse guard for GitHub PR creation, configured by harness.ini."""
import json
import os
import sys

expected = os.environ.get("AGENTIC_BASE_BRANCH", "develop").strip() or "develop"
try:
    actual = json.load(sys.stdin).get("tool_input", {}).get("base", "")
except Exception:
    sys.exit(0)
if actual != expected:
    sys.stderr.write(
        "BLOCKED by pr-base-guard.py: base=%r; configured base is %r.\n" % (actual, expected)
    )
    sys.exit(2)
