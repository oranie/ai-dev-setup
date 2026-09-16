#!/usr/bin/env python3
"""Claude Code の PreToolUse ガード（受け渡しだけを行う）。

**判断は guards/rules.py にある。** Antigravity 側（.agents/hooks/pre_tool_guard.py）と
同じ表を読むので、**2 つのエージェントで判断が食い違うことがない**。
ルールを足すときは guards/rules.py だけを直すこと。

Claude Code のフックは形が違う:
  入力: 標準入力に {"tool_name": "Bash", "tool_input": {"command": "..."}}
  出力: 終了コード 2 ＋ 標準エラーの内容 = 拒否（理由がモデルへ戻る）
        終了コード 0 = 許可
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from guards.rules import evaluate  # noqa: E402

ALLOW, DENY = 0, 2


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return ALLOW
        payload = json.loads(raw)
        if payload.get("tool_name") != "Bash":
            return ALLOW
        verdict = evaluate(payload.get("tool_input", {}).get("command", ""))
        if verdict.allowed:
            return ALLOW
        sys.stderr.write(verdict.reason + "\n")
        return DENY
    except Exception as e:
        # ガードが壊れていることに気づけるよう、必ず標準エラーへ出す。
        # 作業全体を止めないために許可はするが、これが出たら直すこと。
        sys.stderr.write(f"[guard_bash] ガードが動いていません（要修正）: {e}\n")
        return ALLOW


if __name__ == "__main__":
    sys.exit(main())
