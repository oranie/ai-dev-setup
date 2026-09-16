#!/usr/bin/env python3
"""
Antigravity PreInvocation フックスクリプト

モデル推論が開始される直前に、プロンプト品質ゲートの5大受入基準（DoI）および
推測による即座実行（Eager Execution）の禁止指示を注入します。
"""

import sys
import json

GATEKEEPER_REMINDER = (
    "【重要: プロンプト品質ゲート・5大受入基準（DoI）の照合義務】\n"
    "AGENTS.md 第3項に基づき、指示受領直後の推測による即座実行（Eager Execution）を禁止します。\n"
    "以下の5大受入基準（DoI）を照合してください。\n"
    "1. スコープの特定: 変更対象のファイル・関数が名指しされているか（「全部」「あれ」は保留）。\n"
    "2. ドメイン制約・フォールバック: 未来データ除外、欠損時の扱い（NaN等）、按分ルールがあるか。\n"
    "3. 新規技術のリファレンス: docs/references/ のリファレンス調査メモが存在するか。\n"
    "4. 完了条件（DoD）の明示: 具体的なアサーション内容、CI通過基準が明確か。\n"
    "5. 選択の丸投げ検知: 「続けて」「まかせる」に対し、全件実行せず番号確認を行うこと。\n"
    "※ 基準未達時は作業を保留し、ユーザーが番号で回答できる形式で逆質問してください。\n"
    "※ 3ファイル以上の変更、インフラ設定、予測モデル変更時は必ず計画書（implementation_plan）を作成してください。"
)

def main():
    try:
        raw_input = sys.stdin.read()
        if raw_input.strip():
            _ = json.loads(raw_input)

        output = {
            "injectSteps": [
                {
                    "ephemeralMessage": GATEKEEPER_REMINDER
                }
            ]
        }
        print(json.dumps(output, ensure_ascii=False))

    except Exception as e:
        sys.stderr.write(f"PreInvocation hook error: {e}\n")
        print(json.dumps({}))

if __name__ == "__main__":
    main()
