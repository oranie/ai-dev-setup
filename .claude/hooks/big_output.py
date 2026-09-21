#!/usr/bin/env python3
"""大きな出力を本体で受けた直後に、「次は委譲する」と知らせる（PostToolUse hook）。

会話に一度載った出力は、**そのセッションの残り全部のターンで再送される**。
テストの全件出力を 1 回本体で受けるだけで、以降のターンすべてに同じ量が乗り続ける。

委譲の判断は実行の**前**にしか効かないが、大きい出力が来たことに気づけるのは受けた後なので、
ここで「同じ取得を次にするときは向こうに投げる」と一言だけ添える。

サブエージェントの中（入力に agent_id がある）では何も言わない。向こうで受けるのが目的だから。
止めはしない（PostToolUse は止められないし、止める理由も無い）。

判定は `guards/rules.py` と違って**このファイルだけ**にある。Claude Code 固有の仕組みで、
Antigravity 側に対応する層が無いため（`GEMINI.md`）。
"""
import json
import re
import sys

THRESHOLD_CHARS = 20_000   # 約 5,000 トークン。これを超えたら知らせる

# 出力の出どころ → 次に投げる先
HINTS = [
    (r"^Bash$", lambda inp: _bash_hint((inp or {}).get("command") or "")),
    (r"^(Read|Grep|Glob)$", lambda inp: "コードの在処探しは repo-scout（パスと行番号だけ返す）に投げる"),
    (r"^(WebFetch|WebSearch)$", lambda inp: "公式ドキュメントの調査は reference-surveyor に投げ、docs/references/ に書かせる"),
    (r"^mcp__", lambda inp: "外部サービスの大きな応答は general-purpose agent に投げて要点だけ受け取るか、取得条件で絞る"),
]


def _bash_hint(cmd):
    if re.search(r"\b(unittest|pytest|tox|npm (run )?test|yarn test|go test|cargo test|make test)\b", cmd):
        return "テスト・検証の実行は test-runner に投げ、落ちたものだけ受け取る"
    if re.search(r"\b(grep|rg|ag|find|cat|sed|awk)\b", cmd):
        return "コードの在処探しは repo-scout に投げるか、head / tail / grep で絞る"
    if re.search(r"\b(docker|terraform|gcloud|aws|kubectl)\b", cmd):
        return "長いビルド・デプロイのログは test-runner に投げるか、grep で必要な行だけ見る"
    return "出力の大きい実行は test-runner か general-purpose agent に投げるか、head / tail / grep / jq で絞る"


def response_chars(resp):
    """tool_response は文字列のことも、辞書やリストのこともある。会話に載る量として数える"""
    if resp is None:
        return 0
    if isinstance(resp, str):
        return len(resp)
    try:
        return len(json.dumps(resp, ensure_ascii=False))
    except Exception:
        return len(str(resp))


def hint_for(tool_name, tool_input):
    for pat, fn in HINTS:
        if re.search(pat, tool_name or ""):
            return fn(tool_input)
    return "出力の大きい実行はサブエージェントに投げ、要点だけ受け取る（docs/design/subagents.md）"


def evaluate(payload):
    """知らせる文字列。不要なら空文字"""
    if payload.get("agent_id"):
        return ""
    n = response_chars(payload.get("tool_response"))
    if n < THRESHOLD_CHARS:
        return ""
    tool = payload.get("tool_name") or "?"
    return (f"{tool} の出力 {n:,} 字（約 {n // 4:,} トークン）が本体の会話に載りました。"
            f"残りの全ターンで再送されます。次に同じ種類の取得をするときは: "
            f"{hint_for(tool, payload.get('tool_input'))}。")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    note = evaluate(payload)
    if note:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "systemMessage": note}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
