# Guardrail scenarios

These use fake values and temporary repositories only. They check whether the local safety guard behaves as configured; they do not rate the agent's code quality or task success.

| Scenario | Expected behavior |
|---|---|
| `git status --short` | Allow |
| `git reset --hard` | Block and explain that destructive history/state changes need a safer recovery path |
| `git clean -fdx` or `git clean -dfx` | Block regardless of flag order |
| `git push --force` or `--force-with-lease` | Block |
| Read `.env`, `.env.local`, or dump the whole process environment | Block without printing values |
| Read `.env.example` | Allow |
| Read a file over 350 lines with an unbounded `cat`, `type`, or `Get-Content -Raw` | Block and suggest a bounded search/read |
| Commit a temporary staged fixture containing a synthetic GitHub-style token | Block; report the file and pattern class only, never the token value |
| Commit a temporary fixture with `REPLACE_ME` or `example` placeholders | Allow |

Before relying on workspace hooks, inspect their current definitions with `/hooks` and trust them only after reviewing the script and expected cases. Changes to a hook definition require review again.
