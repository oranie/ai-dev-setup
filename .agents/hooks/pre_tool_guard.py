#!/usr/bin/env python3
"""Antigravity の PreToolUse ガード（受け渡しだけを行う）。

**判断は guards/rules.py にある。** ここを直してもルールは変わらない。
ルールを足すときは guards/rules.py を直すこと（Claude Code 側と共通）。

入力: 標準入力に {"toolCall": {"name": ..., "args": {"CommandLine": ...}}}
出力: 標準出力に {"decision": "allow" | "deny", "reason": ...}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from guards.rules import evaluate  # noqa: E402


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({"decision": "allow"}))
            return
        payload = json.loads(raw)
        call = payload.get("toolCall", {})
        if call.get("name") != "run_command":
            print(json.dumps({"decision": "allow"}))
            return
        verdict = evaluate(call.get("args", {}).get("CommandLine", ""))
        if verdict.allowed:
            print(json.dumps({"decision": "allow"}))
        else:
            print(json.dumps({"decision": "deny", "reason": verdict.reason},
                             ensure_ascii=False))
    except Exception as e:
        # **ここで allow を返すと、ガードが壊れていることに誰も気づけない。**
        # 標準エラーへ出したうえで allow にするのは、ガードの不具合で作業全体が
        # 止まるのを避けるため。メッセージが出ていたら必ず直すこと。
        sys.stderr.write(f"[pre_tool_guard] ガードが動いていません（要修正）: {e}\n")
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
