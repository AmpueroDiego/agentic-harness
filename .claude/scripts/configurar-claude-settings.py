"""Merge required harness hooks into a project's Claude settings without replacing its permissions."""
import argparse
import json
from pathlib import Path

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)

def merge(template_path: Path, target_path: Path, base_branch: str) -> None:
    template = json.loads(template_path.read_text(encoding="utf-8"))
    current = json.loads(target_path.read_text(encoding="utf-8")) if target_path.exists() else {}
    current.setdefault("$schema", template.get("$schema"))
    env = current.setdefault("env", {})
    env["AGENTIC_BASE_BRANCH"] = base_branch
    dest_hooks = current.setdefault("hooks", {})
    for event, groups in template.get("hooks", {}).items():
        dest_groups = dest_hooks.setdefault(event, [])
        known = {canonical(g) for g in dest_groups}
        for group in groups:
            if canonical(group) not in known:
                dest_groups.append(group)
                known.add(canonical(group))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--base-branch", required=True)
    a = p.parse_args()
    merge(a.template, a.target, a.base_branch)
