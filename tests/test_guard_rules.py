"""危険コマンドの判定そのものを固定する（guards/rules.py）。

**このファイルが落ちたら、ガードが効いていないか、正当な操作を止めている。**
どちらも実際に起きた:

- `git push --force-with-lease` まで止めていたため、squash マージ後にブランチを
  作り直す運用ができなかった
- `sudo` を前に付けるだけで `rm -rf` の検査を素通りできた
- 説明文（`echo "git add -A は禁止"`）まで止めていたため、回りくどい書き方を誘発した
"""
import unittest

from guards.rules import CONSENT_MARKER, evaluate

# テスト本文に危険なコマンドをそのまま書くと、この規約を導入した環境では
# ガード自身に引っかかる。組み立てて渡す。
ADD, PUSH, COMMIT, RM = "git add", "git push", "git commit", "rm -rf"


class ItStopsWhatItShould(unittest.TestCase):
    def assertDenied(self, command):
        v = evaluate(command)
        self.assertFalse(v.allowed, f"止まっていない: {command!r}")
        self.assertTrue(v.reason and v.reason.strip(), "止めた理由が空")

    def test_staging_everything(self):
        for cmd in (f"{ADD} -A", f"{ADD} .", f"{ADD} --all", f"{ADD} -A ."):
            with self.subTest(cmd=cmd):
                self.assertDenied(cmd)

    def test_committing_unstaged_changes(self):
        for cmd in (f"{COMMIT} -am fix", f"{COMMIT} -a", f"{COMMIT} -a -m x"):
            with self.subTest(cmd=cmd):
                self.assertDenied(cmd)

    def test_force_push(self):
        self.assertDenied(f"{PUSH} --force origin main")
        self.assertDenied(f"{PUSH} origin main --force")

    def test_destructive_delete_even_with_sudo(self):
        """**sudo を前に付けるだけで抜けられてはいけない**"""
        for cmd in (f"{RM} /", f"{RM} ~/work", f"sudo {RM} /etc", f"{RM} ./build"):
            with self.subTest(cmd=cmd):
                self.assertDenied(cmd)

    def test_unrecoverable_git_operations(self):
        self.assertDenied("git clean -fdx")
        self.assertDenied("git reset --hard origin/main")

    def test_skipping_verification(self):
        self.assertDenied(f"{COMMIT} -m fix --no-verify")

    def test_writing_to_block_devices(self):
        self.assertDenied("dd if=/dev/zero of=/dev/sda")
        self.assertDenied("mkfs.ext4 /dev/sdb1")


class ItLetsOrdinaryWorkThrough(unittest.TestCase):
    def assertAllowed(self, command):
        v = evaluate(command)
        self.assertTrue(v.allowed, f"止めてはいけないものを止めている: {command!r}")

    def test_force_with_lease_is_the_safe_one(self):
        """**--force-with-lease は通す。** 他人の作業を消さないための正しい書き方で、
        squash マージ後にブランチを作り直す運用では必須になる"""
        self.assertAllowed(f"{PUSH} --force-with-lease origin feature")
        self.assertAllowed(f"{PUSH} -u --force-with-lease origin feature")

    def test_naming_the_files(self):
        self.assertAllowed(f"{ADD} src/model.py tests/test_model.py")
        self.assertAllowed(f"{ADD} ./src/model.py")
        self.assertAllowed(f"{ADD} .gitignore")

    def test_ordinary_commands(self):
        for cmd in ("pytest tests/", "npm test", "python3 -m unittest discover",
                    f"{COMMIT} -m 'add feature'", "git status", "git diff --stat"):
            with self.subTest(cmd=cmd):
                self.assertAllowed(cmd)

    def test_it_does_not_read_inside_quotes(self):
        """説明文まで止めると、回りくどい書き方を誘発する"""
        self.assertAllowed(f'echo "{ADD} -A は使いません"')
        self.assertAllowed(f"grep -r '{ADD} -A' docs/")

    def test_it_does_not_read_inside_heredocs(self):
        self.assertAllowed(f"cat <<'EOF' > note.md\n{ADD} -A は使いません\nEOF")

    def test_nothing_to_judge(self):
        self.assertAllowed("")
        self.assertAllowed("   ")


class ThereIsAWayThrough(unittest.TestCase):
    """本当に必要なときに回避手段が無いと、エージェントは別の危ない道を探す"""

    def test_the_marker_lets_it_through(self):
        v = evaluate(f"{CONSENT_MARKER} {RM} ./build")
        self.assertTrue(v.allowed, "意図を明示しても通らない")

    def test_the_marker_is_visible_in_the_command(self):
        """印はコマンド行に残るので、何を許したかが記録に残る"""
        self.assertIn("=", CONSENT_MARKER)


if __name__ == "__main__":
    unittest.main()
