# Risk-tiered agent workflow

Use the lightest flow that fits the change. The main agent owns the task and checks the actual diff and evidence before closing it.

| Tier | Typical work | Flow |
|---|---|---|
| 0 — Routine | Clear, reversible edit in a few files; no API, data, security, or external side effect | Main agent works directly. Review the diff and report checks actually run. |
| 1 — Planned | Non-trivial feature or bug with a clear scope and no high-risk boundary | `planner` defines finish conditions and touched paths → `implementer` works to that plan → `qa_reviewer` checks the diff and evidence. |
| 2 — High risk | Auth/security/privacy, schema or data boundaries, concurrency, destructive actions, production or external contracts | `planner` identifies risks and checkpoints → implementation with bounded file ownership → `qa_reviewer` and `adversarial_reviewer` review independently → main agent verifies findings and pauses for user decisions before consequential external or irreversible actions. |

## Coordination rules

- Keep reports structured: `## Plan`, `## QA Review`, or `## Adversarial Review`, ending in `### Result: PASS` or `### Result: FINDINGS`.
- A reviewer verdict is advisory. It never grants permissions or proves that a command, test, or UI check ran.
- Parallel agents must have independent tasks and disjoint write ownership. If work overlaps, sequence it through the main agent.
- Combine findings before asking for a repair. Allow at most two repair/review cycles for the same findings; then stop and report unresolved items.
- Do not add or run tests unless the user asks for testing or verification. When verification is requested, use the owning project's existing scripts and report the exact checks and outcomes.
- For multi-turn work, use a Codex Goal with an observable finish condition. At completion, link the actual evidence in a run record; do not infer completion from the Goal label alone.

## Memory boundaries

- `CodexMemory/adr/` stores decisions about the shared Llama Harness.
- `CodexMemory/runs/` stores only substantial harness-level runs and their evidence.
- Application decisions and application work records belong in the owning project. The root vault must not become a cross-project dump of private context.
- `retro` looks for repeated behavioral failures in run records. `system_auditor` checks the configuration itself. Both propose changes; neither edits operating rules automatically.
