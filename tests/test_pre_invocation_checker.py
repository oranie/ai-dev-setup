import unittest
import json
import subprocess
import sys
import os

class TestPreInvocationChecker(unittest.TestCase):
    script_path = os.path.join(os.path.dirname(__file__), "..", ".agents", "hooks", "pre_invocation_checker.py")

    def run_hook(self, payload_dict_or_str):
        proc = subprocess.Popen(
            [sys.executable, self.script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        input_data = payload_dict_or_str if isinstance(payload_dict_or_str, str) else json.dumps(payload_dict_or_str)
        stdout, stderr = proc.communicate(input=input_data)
        self.assertEqual(proc.returncode, 0, f"Stderr: {stderr}")
        return json.loads(stdout)

    def test_injects_gatekeeper_doi_reminder(self):
        payload = {
            "conversationId": "test-conv-doi",
            "invocationNum": 1,
            "workspacePaths": ["/dummy/workspace"]
        }
        res = self.run_hook(payload)
        self.assertIn("injectSteps", res)
        self.assertEqual(len(res["injectSteps"]), 1)
        msg = res["injectSteps"][0].get("ephemeralMessage", "")
        self.assertIn("プロンプト品質ゲート", msg)
        self.assertIn("5大受入基準", msg)
        self.assertIn("スコープの特定", msg)
        self.assertIn("ドメイン制約", msg)
        self.assertIn("リファレンス", msg)
        self.assertIn("完了条件", msg)
        self.assertIn("選択の丸投げ", msg)

    def test_handles_empty_input(self):
        res = self.run_hook("")
        self.assertIn("injectSteps", res)

    def test_handles_malformed_json_gracefully(self):
        res = self.run_hook("{bad json payload")
        self.assertIsInstance(res, dict)

if __name__ == "__main__":
    unittest.main()
