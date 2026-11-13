import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class BaseGuardTests(unittest.TestCase):
    def test_bash_guard_accepts_configured_and_rejects_other_base(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("Bash unavailable")
        probe = subprocess.run([bash, "--version"], capture_output=True, text=True)
        if probe.returncode != 0:
            self.skipTest("Bash command exists but is not runnable")
        env = dict(os.environ, AGENTIC_BASE_BRANCH="trunk", GIT_GUARD_REPOS=".")
        def run(command):
            return subprocess.run([bash, str(ROOT/".claude/hooks/git-guard.sh")], input=json.dumps({"tool_input":{"command":command}}), text=True, capture_output=True, env=env, cwd=ROOT)
        self.assertEqual(run("gh pr create --base trunk --title test").returncode, 0)
        self.assertEqual(run("gh pr create --base main --title test").returncode, 2)
        self.assertEqual(run("gh pr create --title test").returncode, 2)

    def test_mcp_guard_uses_configured_branch(self):
        env = dict(os.environ, AGENTIC_BASE_BRANCH="trunk")
        def run(base):
            return subprocess.run([sys.executable, str(ROOT/".claude/hooks/pr-base-guard.py")], input=json.dumps({"tool_input":{"base":base}}), text=True, capture_output=True, env=env)
        self.assertEqual(run("trunk").returncode, 0)
        self.assertEqual(run("develop").returncode, 2)

if __name__ == "__main__":
    unittest.main()
