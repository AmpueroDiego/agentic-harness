"""PreToolUse(mcp__github__create_pull_request) - misma regla que git-guard.sh
para el otro camino por el que se puede abrir un PR: el MCP de GitHub."""
import sys, json
try:
    base = json.load(sys.stdin).get("tool_input", {}).get("base", "")
except Exception:
    sys.exit(0)
if base != "develop":
    sys.stderr.write(
        "BLOQUEADO por .claude/hooks/pr-base-guard.py - base=%r.\n"
        "Los PRs de AcmeOrg van contra 'develop' (flujo develop -> qa -> main).\n" % base)
    sys.exit(2)
