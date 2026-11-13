import json
import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class InstallSmokeTests(unittest.TestCase):
    def test_fresh_install_and_idempotent_settings_merge(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("Bash unavailable")
        probe = subprocess.run([bash, "--version"], capture_output=True, text=True)
        if probe.returncode != 0:
            self.skipTest("Bash command exists but is not runnable")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            subprocess.run(["git", "init", str(target)], check=True, capture_output=True)
            (target / ".claude").mkdir()
            (target / ".claude/settings.json").write_text(json.dumps({"permissions":{"allow":["Bash(git status:*)"]}}), encoding="utf-8")
            ini = Path(tmp) / "harness.ini"
            ini.write_text("[project]\nname = Demo\n[git]\nbase_branch = trunk\n", encoding="utf-8")
            cmd = [bash, str(ROOT / "install.sh"), "--target", str(target), "--ini", str(ini)]
            subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True, text=True)
            settings = json.loads((target / ".claude/settings.json").read_text(encoding="utf-8"))
            self.assertEqual(settings["permissions"]["allow"], ["Bash(git status:*)"])
            self.assertEqual(settings["env"]["AGENTIC_BASE_BRANCH"], "trunk")
            self.assertTrue((target / ".claude/workflows/orquestar-medio.js").is_file())
            self.assertTrue((target / ".agents/skills/orquestar/SKILL.md").is_file())
            subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True, text=True)
            self.assertFalse(list(target.rglob("*.bak")))

if __name__ == "__main__":
    unittest.main()
