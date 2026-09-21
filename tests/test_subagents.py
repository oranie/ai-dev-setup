"""**委譲の仕組みが静かに壊れていないか**を確かめる。

サブエージェントは「出力の大きい実行を本体の会話に持ち込まない」ための層（`docs/design/subagents.md`）。
壊れ方が静かなのが厄介で、次のどれが起きても**その場では誰も気づかない**。

- `model:` をエイリアス（`sonnet`）で書くと、プロバイダによって世代が 2 つ変わる
- 読むだけの係に `Write` が付くと、判断が手元から離れる
- `CLAUDE.md` の表に無い agent は、存在を知られないまま腐る
- `skills:` の指し先が無いと、黙って空になる

frontmatter のパースに PyYAML は使わない。依存を増やすと
「手元で通って CI で ModuleNotFoundError」を踏む（AGENTS.md 2-A-7）。
"""
import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(ROOT, ".claude", "agents")

# 足すときは docs/design/subagents.md の 7 節を読んでから、ここにも足すこと
EXPECTED = ("test-runner", "repo-scout", "reference-surveyor", "implementer", "implementer-lite")
# **書き込めるのはこの 3 本だけ。** 緩めるときは理由を docs/design/subagents.md に書く
WRITABLE = ("reference-surveyor", "implementer", "implementer-lite")
READ_ONLY = ("test-runner", "repo-scout")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def frontmatter(text):
    """`---` で挟まれた先頭ブロックを、`key: value` の辞書として読む（PyYAML は使わない）"""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    data = {}
    for line in match.group(1).splitlines():
        if re.match(r"^\s", line) or ":" not in line:
            continue                       # 継続行（description の折り返し等）は読み飛ばす
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def tool_list(value):
    return [t.strip() for t in (value or "").split(",") if t.strip()]


class EveryAgentIsDefined(unittest.TestCase):
    def test_the_expected_agents_exist(self):
        found = sorted(f[:-3] for f in os.listdir(AGENTS_DIR) if f.endswith(".md"))
        self.assertEqual(found, sorted(EXPECTED),
                         "定義の数が想定と違う。足したなら EXPECTED と "
                         "CLAUDE.md 3 節の表にも足すこと")

    def test_the_name_matches_the_filename(self):
        """呼び出しに使われるのは `name`。ファイル名とずれると呼べない"""
        for agent in EXPECTED:
            with self.subTest(agent=agent):
                self.assertEqual(frontmatter(_read(".claude", "agents", f"{agent}.md")).get("name"),
                                 agent, f"{agent}.md の name がファイル名と違う")

    def test_every_agent_says_when_to_use_it(self):
        """`description` を見て呼ぶかが決まる。空だと呼ばれない"""
        for agent in EXPECTED:
            with self.subTest(agent=agent):
                desc = frontmatter(_read(".claude", "agents", f"{agent}.md")).get("description", "")
                self.assertGreater(len(desc), 20, f"{agent} の description が短すぎる")


class TheModelIsPinned(unittest.TestCase):
    """**エイリアスで書かないこと。**

    `sonnet` はプロバイダごとの推奨版に解決される（Anthropic API なら Sonnet 5、
    Bedrock なら Sonnet 4.5 といった具合に世代が変わる）。委譲先が黙って入れ替わらないよう、
    フル ID で固定する。
    """

    def test_every_model_is_a_full_id(self):
        for agent in EXPECTED:
            with self.subTest(agent=agent):
                model = frontmatter(_read(".claude", "agents", f"{agent}.md")).get("model", "")
                self.assertRegex(model, r"^claude-[a-z]+-\d",
                                 f"{agent} の model がフル ID でない: {model!r}")


class WritingStaysInThreeAgents(unittest.TestCase):
    def test_the_read_only_agents_cannot_write(self):
        for agent in READ_ONLY:
            with self.subTest(agent=agent):
                front = frontmatter(_read(".claude", "agents", f"{agent}.md"))
                denied = tool_list(front.get("disallowedTools"))
                for tool in ("Write", "Edit"):
                    self.assertIn(tool, denied,
                                  f"{agent} が {tool} を禁止していない。"
                                  "回す係・探す係が直し始めると判断が手元から離れる")
                self.assertNotIn("Write", tool_list(front.get("tools")))

    def test_no_fourth_agent_can_write(self):
        writable = []
        for agent in EXPECTED:
            front = frontmatter(_read(".claude", "agents", f"{agent}.md"))
            if {"Write", "Edit"} & set(tool_list(front.get("tools"))):
                writable.append(agent)
        self.assertEqual(sorted(writable), sorted(WRITABLE),
                         "書き込める agent の顔ぶれが変わっている。"
                         "緩めるなら docs/design/subagents.md に理由を書くこと")

    def test_the_surveyor_only_creates_files(self):
        front = frontmatter(_read(".claude", "agents", "reference-surveyor.md"))
        self.assertIn("Edit", tool_list(front.get("disallowedTools")),
                      "reference-surveyor は docs/references/ に新規で書くだけ")


class DangerousWorkIsNotDelegated(unittest.TestCase):
    """**本番に影響する操作は手元に残す。** 実装は委譲したが、ここは委譲していない"""

    def test_the_writers_refuse_push_and_merge(self):
        for agent in ("implementer", "implementer-lite"):
            body = _read(".claude", "agents", f"{agent}.md")
            for word in ("git push", "PR の作成", "マージ"):
                with self.subTest(agent=agent, word=word):
                    self.assertIn(word, body, f"{agent} の本文から「{word}」の禁止が消えている")

    def test_the_writers_stop_when_the_plan_runs_out(self):
        for agent in ("implementer", "implementer-lite"):
            with self.subTest(agent=agent):
                self.assertIn("止ま", _read(".claude", "agents", f"{agent}.md"),
                              f"{agent} に「プランに無い判断が出たら止まる」が無い。"
                              "判断が手元から離れる")


class TheSkillReferenceResolves(unittest.TestCase):
    def test_every_referenced_skill_exists(self):
        """`skills:` の指し先が無いと、黙って空になる"""
        for agent in EXPECTED:
            front = frontmatter(_read(".claude", "agents", f"{agent}.md"))
            for skill in tool_list(front.get("skills")):
                with self.subTest(agent=agent, skill=skill):
                    self.assertTrue(
                        os.path.isfile(os.path.join(ROOT, ".claude", "skills", skill, "SKILL.md")),
                        f"{agent} が指す skill {skill} が無い")


class TheDocsKnowEveryAgent(unittest.TestCase):
    """表に無い agent は、存在を知られないまま腐る"""

    def test_claude_md_lists_them_all(self):
        body = _read("CLAUDE.md")
        for agent in EXPECTED:
            with self.subTest(agent=agent):
                self.assertIn(agent, body, f"CLAUDE.md 3 節の表に {agent} が無い")

    def test_the_design_doc_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "docs", "design", "subagents.md")))


class TheBigOutputHookNudges(unittest.TestCase):
    """大きい出力を受けたことに気づけるか（`docs/design/subagents.md` 1 節）"""

    def _run(self, payload):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, ".claude", "hooks", "big_output.py")],
            input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def test_a_big_output_gets_a_hint(self):
        out = self._run({"tool_name": "Bash",
                         "tool_input": {"command": "python3 -m unittest discover tests"},
                         "tool_response": "x" * 30_000})
        self.assertIn("test-runner", out, "テストの大量出力で test-runner を勧めていない")

    def test_a_small_output_stays_quiet(self):
        self.assertEqual(self._run({"tool_name": "Bash", "tool_input": {"command": "ls"},
                                    "tool_response": "a\nb\n"}), "",
                         "小さい出力にまで口を出すと、注意書きが読み飛ばされる")

    def test_it_stays_quiet_inside_a_subagent(self):
        """向こうで受けるのが目的なので、サブエージェントの中では言わない"""
        self.assertEqual(self._run({"tool_name": "Bash", "agent_id": "abc",
                                    "tool_input": {"command": "python3 -m unittest discover tests"},
                                    "tool_response": "x" * 30_000}), "")

    def test_broken_input_does_not_break_the_turn(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, ".claude", "hooks", "big_output.py")],
            input="{not json", capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
