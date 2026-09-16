"""危険なコマンドを止めるルールの**唯一の定義**。

## なぜ 1 ファイルに集めるか

以前はガードスクリプトが 3 箇所に同じ内容でコピーされており、テストが見ていたのは
そのうちの 1 つ、フックが実際に呼ぶのは別の 1 つだった。3 つが同一である間は誰も
気づかないが、**片方を直した瞬間にテストは緑のままガードだけ古くなる**。

エージェントごとの差は「入出力の形」だけなので、**判断はここに集め、各エージェント
向けのファイルは受け渡しだけを行う**:

    .agents/hooks/pre_tool_guard.py   Antigravity 形式（JSON in / JSON out）
    .claude/hooks/guard_bash.py       Claude Code 形式（JSON in / 終了コード）

どちらも `evaluate()` を呼ぶだけにしてある。ルールを足すときはここだけを直す。
"""
import re
from typing import NamedTuple, Optional


class Verdict(NamedTuple):
    allowed: bool
    reason: Optional[str] = None


# (正規表現, 止める理由)。理由は**実行者が次に何をすればよいか**まで書く。
# 「禁止です」だけでは、エージェントは回避策を探して別の危ないことをする。
RULES = [
    (
        # `git add -A` / `--all` / `.`。パス指定（git add ./src/x.py）は通す
        r"\bgit\s+add\s+(?:-A|--all|\.)(?:\s|$)",
        "git add -A / git add . は使いません。作業ディレクトリに置かれた認証ファイルや"
        "ビルド成果物を巻き込みます。\n"
        "入れるファイルを名指ししてください。例: git add src/model.py tests/test_model.py",
    ),
    (
        # `git commit -a` / `-am`。`-m` だけは通す
        r"\bgit\s+commit\b[^|;&]*\s-[a-zA-Z]*a[a-zA-Z]*\b",
        "git commit -a / -am は、ステージしていない差分まで黙って入れます。\n"
        "git add <ファイル> で対象を決めてからコミットしてください。",
    ),
    (
        # 強制 push。**--force-with-lease は通す**（下の説明を参照）
        r"\bgit\s+push\b[^|;&]*\s--force(?!-with-lease)\b",
        "git push --force はリモートの履歴を無条件に上書きします。\n"
        "他人の作業を消さない --force-with-lease を使ってください。",
    ),
    (
        # 履歴や作業ツリーを戻せなくする操作
        r"\bgit\s+(?:clean\s+-[a-zA-Z]*[fd][a-zA-Z]*|reset\s+--hard)\b",
        "git clean -fd / git reset --hard は、コミットしていない変更を戻せません。\n"
        "捨ててよいか確かめ、必要なら git stash で退避してから実行してください。",
    ),
    (
        # 破壊的な削除。sudo が前に付いても効くよう、パスの形を限定しない
        r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+\S",
        "rm -rf は取り消せません。消す対象が本当に再生成できるものか確かめ、\n"
        "必要なら対象を名指しして 1 つずつ消してください。",
    ),
    (
        # ディスクへの直接書き込み
        r"\b(?:dd\s+[^|;&]*\bof=/dev/|mkfs(?:\.\w+)?\s+/dev/)",
        "ブロックデバイスへの直接書き込みは、環境を復旧できない状態にします。",
    ),
    (
        # 検証を飛ばしてコミットする
        r"--no-verify\b",
        "--no-verify は、コミット前の検査を飛ばします。\n"
        "検査が邪魔なら、検査のほうを直してください。",
    ),
]

# `rm -rf` のように「常に危ないわけではない」ものは、この印を付ければ通す。
# 環境変数と同じ形にしてあるので、実行者が意図を明示したことが記録に残る。
CONSENT_MARKER = "AI_DEV_ALLOW_DESTRUCTIVE=1"


def _strip_quoted(command: str) -> str:
    """引用符とヒアドキュメントの中身を外す。

    `echo "git add -A は禁止"` のような**説明文**まで止めてしまうと、
    エージェントはガードを避けるために回りくどい書き方を始める。
    止めたいのは実行されるコマンドだけ。
    """
    without_heredoc = re.sub(r"<<-?\s*'?(\w+)'?.*?^\1", " ", command,
                             flags=re.S | re.M)
    without_quotes = re.sub(r"'[^']*'|\"[^\"]*\"", " ", without_heredoc)
    return without_quotes


def evaluate(command: str) -> Verdict:
    """1 つのコマンド行を見て、通すか止めるかを決める"""
    if not command or not command.strip():
        return Verdict(True)
    if CONSENT_MARKER in command:
        return Verdict(True)
    flat = _strip_quoted(command)
    for pattern, reason in RULES:
        if re.search(pattern, flat):
            return Verdict(False, reason)
    return Verdict(True)
