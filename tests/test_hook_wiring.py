"""**設定に書いたフックが、実際に存在して動くか**を確かめる。

## なぜこのテストがあるか

`hooks.json` は `python3 ./hooks/pre_tool_guard.py` を指していたが、そのパスは
**リポジトリのルートからは解決しなかった**（実体は `.agents/hooks/` 配下）。
しかもガードは例外時に「許可」を返す作りなので、**スクリプトが見つからなくても
黙って素通りする**。看板にしている機能が、壊れていることに気づけない状態だった。

同じ理由で、ガードスクリプトが 3 箇所へコピーされ、テストが見ているのはそのうちの
1 つ、フックが呼ぶのは別の 1 つ、という状態にもなっていた。3 つが同一である間は
誰も気づかないが、**片方を直した瞬間にテストは緑のままガードだけ古くなる**。

このファイルは「設定と実体がつながっていること」だけを見る。
"""
import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class EveryConfiguredHookExists(unittest.TestCase):
    """設定ファイルが名指ししたスクリプトが、その場所に実在すること"""

    def _path_in(self, command):
        """設定に書かれた .py を、リポジトリルート基準の相対パスとして取り出す。

        `${CLAUDE_PROJECT_DIR}/...` のような変数展開と、先頭の `./` を落とす。
        """
        raw = re.search(r"[^\s\"']+\.py", command)
        self.assertIsNotNone(raw, f"コマンドから .py を読み取れない: {command!r}")
        path = raw.group(0)
        path = re.sub(r"^.*\}", "", path)        # ${VAR} を落とす
        # lstrip は「文字の集合」を削るので "./" を渡すと .agents の先頭の
        # ドットまで消える。前置きは 1 つずつ外す
        if path.startswith("./"):
            path = path[2:]
        return path.lstrip("/")

    def test_the_antigravity_hooks_resolve(self):
        config = json.loads(_read(".agents", "hooks.json"))
        commands = []
        for group in config.values():
            for entry in (group.get("PreToolUse") or []):
                commands += [h["command"] for h in entry["hooks"]]
            for entry in (group.get("PreInvocation") or []):
                commands.append(entry["command"])
        self.assertTrue(commands, "hooks.json からフックを 1 つも読み取れていない")
        for command in commands:
            with self.subTest(command=command):
                path = self._path_in(command)
                self.assertTrue(
                    os.path.isfile(os.path.join(ROOT, path)),
                    f"hooks.json が指す {path} がリポジトリルートから見つからない。"
                    "フックは黙って素通りする")

    def test_the_claude_code_hooks_resolve(self):
        config = json.loads(_read(".claude", "settings.json"))
        commands = [h["command"]
                    for entry in config["hooks"]["PreToolUse"]
                    for h in entry["hooks"]]
        self.assertTrue(commands, "settings.json からフックを 1 つも読み取れていない")
        for command in commands:
            with self.subTest(command=command):
                path = self._path_in(command)
                self.assertTrue(os.path.isfile(os.path.join(ROOT, path)),
                                f"settings.json が指す {path} が見つからない")


class TheRulesLiveInExactlyOnePlace(unittest.TestCase):
    """判定の表が増殖していないこと"""

    def test_there_is_a_single_rule_table(self):
        from guards import rules
        self.assertTrue(rules.RULES, "ルールが空")
        copies = []
        for dirpath, _dirs, files in os.walk(ROOT):
            if ".git" in dirpath:
                continue
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                if os.path.relpath(path, ROOT).startswith(("guards", "tests")):
                    continue
                with open(path, encoding="utf-8") as f:
                    if "DANGEROUS_PATTERNS" in f.read():
                        copies.append(os.path.relpath(path, ROOT))
        self.assertEqual(copies, [],
                         f"判定の表が guards/rules.py の外にもある: {copies}。"
                         "片方だけ直して食い違う")

    def test_the_adapters_only_pass_things_through(self):
        """各エージェント向けのファイルは、判定を自前で持たないこと"""
        for adapter in (os.path.join(".agents", "hooks", "pre_tool_guard.py"),
                        os.path.join(".claude", "hooks", "guard_bash.py")):
            with self.subTest(adapter=adapter):
                body = _read(adapter)
                self.assertIn("from guards.rules import evaluate", body,
                              f"{adapter} が共通のルールを読んでいない")


class BothAgentsDecideTheSame(unittest.TestCase):
    """**2 つのエージェントで判断が食い違わないこと。**

    片方だけ緩いと、そちらのエージェントを使ったときだけ事故が起きる。
    """

    SHARED = [
        ("git add" + " -A", False),
        ("git add" + " src/model.py", True),
        ("git commit" + " -am fix", False),
        ("git push" + " --force origin main", False),
        ("git push" + " --force-with-lease origin feature", True),
        ("sudo " + "rm -rf" + " /etc", False),
        ("pytest tests/", True),
    ]

    def _antigravity(self, command):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, ".agents", "hooks", "pre_tool_guard.py")],
            input=json.dumps({"toolCall": {"name": "run_command",
                                           "args": {"CommandLine": command}}}),
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)["decision"] == "allow"

    def _claude_code(self, command):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, ".claude", "hooks", "guard_bash.py")],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
            capture_output=True, text=True)
        self.assertIn(proc.returncode, (0, 2), proc.stderr)
        return proc.returncode == 0

    def test_they_agree_on_every_case(self):
        for command, should_allow in self.SHARED:
            with self.subTest(command=command):
                a, c = self._antigravity(command), self._claude_code(command)
                self.assertEqual(a, should_allow, f"Antigravity 側の判断が違う: {command!r}")
                self.assertEqual(c, should_allow, f"Claude Code 側の判断が違う: {command!r}")

    def test_a_denial_explains_itself(self):
        """止めるときは理由を返すこと。理由が無いと回避策を探し始める"""
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, ".claude", "hooks", "guard_bash.py")],
            input=json.dumps({"tool_name": "Bash",
                              "tool_input": {"command": "git add" + " -A"}}),
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertTrue(proc.stderr.strip(), "止めた理由がモデルへ返っていない")


class TheSkillsAreTheSameForBothAgents(unittest.TestCase):
    """スキルは両方のディレクトリに置く必要があるので、**中身が一致すること**を縛る"""

    SKILLS = ("reference-survey", "leak-and-wiring-audit", "code-quality-audit")

    def test_every_skill_exists_on_both_sides(self):
        for skill in self.SKILLS:
            for base in (".agents", ".claude"):
                with self.subTest(skill=skill, base=base):
                    self.assertTrue(
                        os.path.isfile(os.path.join(ROOT, base, "skills", skill, "SKILL.md")),
                        f"{base}/skills/{skill}/SKILL.md が無い。"
                        "そのエージェントではこのスキルが呼べない")

    def test_the_bodies_match(self):
        for skill in self.SKILLS:
            with self.subTest(skill=skill):
                self.assertEqual(
                    _read(".agents", "skills", skill, "SKILL.md"),
                    _read(".claude", "skills", skill, "SKILL.md"),
                    f"{skill} の内容が 2 つのディレクトリで食い違っている")


if __name__ == "__main__":
    unittest.main()
