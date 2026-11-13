import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class WindowsInstallTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows PowerShell installer")
    def test_installs_hooks_workflow_and_skills_idempotently(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        self.assertIsNotNone(shell)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); target = base/"target"; target.mkdir()
            subprocess.run(["git", "init", str(target)], check=True, capture_output=True)
            (target/".claude").mkdir()
            (target/".claude/settings.json").write_text(json.dumps({"permissions":{"allow":["Bash(git status:*)"]}}), encoding="utf-8")
            ini = base/"harness.ini"
            ini.write_text("[project]\nname = Demo\n[git]\nbase_branch = trunk\n", encoding="utf-8")
            cmd=[shell,"-NoProfile","-File",str(ROOT/"install.ps1"),"-Target",str(target),"-Ini",str(ini)]
            result=subprocess.run(cmd,check=False,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            config=json.loads((target/".claude/settings.json").read_text(encoding="utf-8"))
            self.assertEqual(config["permissions"]["allow"],["Bash(git status:*)"])
            self.assertEqual(config["env"]["AGENTIC_BASE_BRANCH"],"trunk")
            self.assertTrue((target/".claude/workflows/orquestar-medio.js").is_file())
            self.assertTrue((target/".agents/skills/orquestar/SKILL.md").is_file())
            result=subprocess.run(cmd,check=False,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse(list(target.rglob("*.bak")))

if __name__ == "__main__":
    unittest.main()
