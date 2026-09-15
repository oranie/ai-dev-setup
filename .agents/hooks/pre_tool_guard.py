#!/usr/bin/env python3
"""
Antigravity PreToolUse ガードスクリプト

run_command の実行前に危険なコマンドや誤操作パターンを検査し、
誤コミット（git add -A等）や破壊的コマンドをブロックします。
"""

import sys
import json
import re

# ブロック対象のコマンドパターンと理由
DANGEROUS_PATTERNS = [
    (
        r"\bgit\s+add\s+(-A|--all|\.)(\s|$)",
        "git add -A / git add . は機密情報やビルドキャッシュの誤コミットを防ぐため禁止されています。変更対象ファイルを明示して 'git add <ファイルパス>' を実行してください。"
    ),
    (
        r"\bgit\s+commit\s+-[a-zA-Z]*a[a-zA-Z]*\b",
        "git commit -a / -am は意図しない差分の自動コミットを防ぐため非推奨です。対象ファイルを個別にステージングした上でコミットしてください。"
    ),
    (
        r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+(/|/\*|\.)(?:\s|$)",
        "ルートまたはカレント全域に対する破壊的削除コマンドは禁止されています。"
    ),
    (
        r"\bgit\s+push\s+.*--force\b",
        "強制プッシュ (git push --force) はリモート履歴の破壊を防ぐためブロックされました。"
    )
]

def evaluate_command(command_line: str):
    cmd = command_line.strip()
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            return {
                "decision": "deny",
                "reason": reason
            }
    return {
        "decision": "allow"
    }

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        if tool_name == "run_command":
            cmd = tool_args.get("CommandLine", "")
            result = evaluate_command(cmd)
            print(json.dumps(result, ensure_ascii=False))
            return

        # その他のツールは許可
        print(json.dumps({"decision": "allow"}))

    except Exception as e:
        # スクリプト自体で例外が発生した場合は安全のためaskまたはallowにする
        sys.stderr.write(f"Guard error: {e}\n")
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
