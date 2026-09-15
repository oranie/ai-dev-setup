import unittest
import json
import subprocess
import sys
import os

class TestPreToolGuard(unittest.TestCase):
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks", "pre_tool_guard.py")

    def run_guard(self, payload):
        proc = subprocess.Popen(
            [sys.executable, self.script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=json.dumps(payload))
        self.assertEqual(proc.returncode, 0, f"Stderr: {stderr}")
        return json.loads(stdout)

    def test_blocks_git_add_all(self):
        dangerous_commands = [
            "git add -A",
            "git add .",
            "git add --all",
            "git add -A .",
        ]
        for cmd in dangerous_commands:
            payload = {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": cmd}
                }
            }
            res = self.run_guard(payload)
            self.assertEqual(res.get("decision"), "deny", f"Failed to block: {cmd}")
            self.assertIn("禁止されています", res.get("reason", ""))

    def test_blocks_git_commit_auto(self):
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git commit -am 'quick fix'"}
            }
        }
        res = self.run_guard(payload)
        self.assertEqual(res.get("decision"), "deny")

    def test_blocks_dangerous_rm_and_force_push(self):
        payload_rm = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "rm -rf /"}
            }
        }
        res_rm = self.run_guard(payload_rm)
        self.assertEqual(res_rm.get("decision"), "deny")

        payload_push = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git push origin main --force"}
            }
        }
        res_push = self.run_guard(payload_push)
        self.assertEqual(res_push.get("decision"), "deny")

    def test_allows_safe_commands(self):
        safe_commands = [
            "git add src/model.py",
            "git add docs/references/template.md",
            "pytest tests/",
            "npm test",
            "python3 -m unittest discover",
        ]
        for cmd in safe_commands:
            payload = {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": cmd}
                }
            }
            res = self.run_guard(payload)
            self.assertEqual(res.get("decision"), "allow", f"Unexpectedly blocked: {cmd}")

    def test_allows_other_tools(self):
        payload = {
            "toolCall": {
                "name": "view_file",
                "args": {"AbsolutePath": "/dummy/path"}
            }
        }
        res = self.run_guard(payload)
        self.assertEqual(res.get("decision"), "allow")

if __name__ == "__main__":
    unittest.main()
