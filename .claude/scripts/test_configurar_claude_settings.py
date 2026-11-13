import json
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
_spec = importlib.util.spec_from_file_location("configurar_claude_settings", Path(__file__).resolve().parent / "configurar-claude-settings.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
merge = _module.merge

class MergeSettingsTests(unittest.TestCase):
    def test_preserves_permissions_and_merges_hooks_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); template = base/"template.json"; target = base/"settings.json"
            template.write_text(json.dumps({"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"guard"}]}]}}), encoding="utf-8")
            target.write_text(json.dumps({"permissions":{"allow":["Bash(git status:*)"]},"hooks":{"PostToolUse":[]}}), encoding="utf-8")
            merge(template, target, "trunk"); merge(template, target, "trunk")
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["permissions"]["allow"], ["Bash(git status:*)"])
            self.assertEqual(result["env"]["AGENTIC_BASE_BRANCH"], "trunk")
            self.assertEqual(len(result["hooks"]["PreToolUse"]), 1)

if __name__ == "__main__":
    unittest.main()
