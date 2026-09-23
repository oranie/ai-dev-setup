"""**スキルが呼べる形になっているか**を確かめる。

スキルの壊れ方は静かです。`name` がディレクトリ名とずれていても、本文が実在しないファイルを
指していても、読むまでは分かりません。ここで見るのは次の 4 つ。

- `name` がディレクトリ名と一致するか（呼び出しに使われるのは `name`）
- 本文が指すファイルが実在するか（空振りの手順書になる）
- **両方のエージェントに置いたスキルが、一致の検査から漏れていないか**
  （`tests/test_hook_wiring.py` が見ているのは固定の 3 つ。4 つ目を両方に置くと検査から外れる）
- Claude Code 固有のスキルが `CLAUDE.md` に書いてあるか（書いていないものは呼ばれない）

frontmatter のパースに PyYAML は使わない。ロックファイルに無い依存を足すと、
手元で通って CI で落ちる（AGENTS.md 2-A-7）。
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Claude Code でしか意味を持たないスキル。`.agents/skills` には置かない
CLAUDE_ONLY = ("land",)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def skills_in(base):
    path = os.path.join(ROOT, base, "skills")
    if not os.path.isdir(path):
        return set()
    return {name for name in os.listdir(path)
            if os.path.isfile(os.path.join(path, name, "SKILL.md"))}


def frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    data = {}
    for line in (match.group(1).splitlines() if match else []):
        if re.match(r"^\s", line) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


class EverySkillCanBeCalled(unittest.TestCase):
    def test_the_name_matches_the_directory(self):
        for base in (".claude", ".agents"):
            for skill in sorted(skills_in(base)):
                with self.subTest(base=base, skill=skill):
                    front = frontmatter(_read(base, "skills", skill, "SKILL.md"))
                    self.assertEqual(front.get("name"), skill,
                                     f"{base}/skills/{skill} の name がディレクトリ名と違う")

    def test_every_skill_says_when_to_use_it(self):
        for base in (".claude", ".agents"):
            for skill in sorted(skills_in(base)):
                with self.subTest(base=base, skill=skill):
                    text = _read(base, "skills", skill, "SKILL.md")
                    front = frontmatter(text)
                    desc = front.get("description", "")
                    if desc in (">-", "|"):        # 折り返し記法。本文側に書かれている
                        desc = text.split("---", 2)[1]
                    self.assertGreater(len(desc), 20, f"{skill} の description が短すぎる")


class SkillsDoNotPointAtNothing(unittest.TestCase):
    """本文が指すリポジトリ内のファイルが実在すること。空振りの指示になる"""

    # 例示として書かれるパスは拾わない。リポジトリの実体を指す場所だけを見る
    TRACKED = (".github/", ".claude/", ".agents/", "docs/", "guards/", "tests/")

    def test_referenced_files_exist(self):
        for base in (".claude", ".agents"):
            for skill in sorted(skills_in(base)):
                body = _read(base, "skills", skill, "SKILL.md")
                for path in re.findall(r"`([\w./-]+\.(?:py|md|json|yml))`", body):
                    if not path.startswith(self.TRACKED):
                        continue
                    with self.subTest(skill=skill, path=path):
                        self.assertTrue(os.path.exists(os.path.join(ROOT, path)),
                                        f"{base}/skills/{skill} が指す {path} が無い")


class SharedSkillsStayUnderTheParityCheck(unittest.TestCase):
    """**両方に置いたスキルが、一致の検査から漏れていないこと。**

    `tests/test_hook_wiring.py` の `SKILLS` は固定の並び。両方のディレクトリに 4 つ目を
    置いても、そこに足さない限り**中身が食い違っても誰も気づかない**。
    """

    def _parity_list(self):
        source = _read("tests", "test_hook_wiring.py")
        listed = re.search(r"SKILLS\s*=\s*\(([^)]*)\)", source)
        self.assertIsNotNone(listed, "test_hook_wiring.py から SKILLS を読み取れない")
        return set(re.findall(r'"([^"]+)"', listed.group(1)))

    def test_the_parity_list_covers_every_shared_skill(self):
        shared = skills_in(".claude") & skills_in(".agents")
        self.assertEqual(shared, self._parity_list(),
                         "両方に置いたスキルと、一致を検査しているスキルが食い違っている")

    def test_the_claude_only_skills_are_not_duplicated(self):
        for skill in CLAUDE_ONLY:
            with self.subTest(skill=skill):
                self.assertIn(skill, skills_in(".claude"), f"{skill} が .claude/skills に無い")
                self.assertNotIn(skill, skills_in(".agents"),
                                 f"{skill} は Claude Code 固有。両方に置くなら "
                                 "test_hook_wiring.py の SKILLS にも足すこと")


class LandIsWiredUp(unittest.TestCase):
    """PR を着地させる手順（AGENTS.md 2-A-10）の実行役"""

    def test_claude_md_points_at_it(self):
        self.assertIn("/land", _read("CLAUDE.md"), "CLAUDE.md に /land の案内が無い")

    def test_the_rule_exists_for_other_tools(self):
        """スキルを持たないツールでも手順を踏めるよう、規約側にも書いてあること"""
        self.assertIn("2-A-10", _read("AGENTS.md"))
        self.assertIn("2-A-10", _read("GEMINI.md"),
                      "Antigravity 側に、手で踏む手順への案内が無い")

    def test_it_does_not_poll_with_sleep(self):
        body = _read(".claude", "skills", "land", "SKILL.md")
        self.assertIn("--watch", body, "CI を待つ手段が書かれていない")
        self.assertRegex(body, r"sleep.{0,20}ポーリングしない",
                         "sleep でのポーリングを禁じる行が消えている")

    def test_it_does_not_create_the_pr(self):
        """PR を作るのは呼び出し元。ここで作ると二重に出る"""
        self.assertIn("PR を作りません", _read(".claude", "skills", "land", "SKILL.md"))


if __name__ == "__main__":
    unittest.main()
