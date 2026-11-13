"""Print anonymized golden tasks for repeatable manual agent evaluation."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/runs/golden-tasks.json"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Only print one task, e.g. GT-03")
    args = parser.parse_args()
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tasks = data["tasks"]
    if args.id:
        tasks = [task for task in tasks if task["id"] == args.id]
        if not tasks:
            parser.error(f"unknown task id: {args.id}")
    for task in tasks:
        print(f"## {task['id']} — {task['name']}\n\n{task['prompt']}\n\nChecks:")
        for check in task["checks"]:
            print(f"- [ ] {check}")
        print()

if __name__ == "__main__":
    main()
