---
name: code-quality-audit
description: >-
  Use this skill to audit codebase quality, test integrity, CSS rules, and infrastructure setups.
  Detects missing test assertions, CSS !important violations, browser alert/confirm calls, and Docker context issues.
---

# コード品質・テスト監査スキル (code-quality-audit)

このスキルは、形骸化したテストコード、UI・CSSのアンチパターン、インフラ設定の落とし穴を検出し、コードベースの保守性と安全性を確保するための監査手順書です。

---

## 監査項目と手順

### 1. テスト品質と形骸化テストの検査
「CIが通るが実際には何も検査していない」状態を排除します。

1. **アサーション（assert）の存在確認**:
   - すべてのテスト関数に、具体的な期待値との比較アサーションが含まれていることを確認する。
   - 例外が発生しないことだけを確認するテスト（関数の呼び出しのみで終わるテスト）がないか走査する。
2. **スタブ・モックの妥当性確認**:
   - モックが本番と乖離していないか、テスト対象ロジックの判定をスキップさせていないかを確認する。

### 2. UI・フロントエンドの静的検査
保守性を損なうUI実装や、不自然な画面挙動を検出します。

1. **CSS `!important` の検出**:
   - CSSファイル内に `!important` が含まれていないかを走査する。
   ```bash
   grep -rn "!important" frontend/ src/ styles/
   ```
   - 発見した場合は、セレクタ詳細度の調整またはCSS変数の使用に修正する。
2. **ブラウザ標準ダイアログの検出**:
   - ソースコード内に `alert(`, `confirm(`, `prompt(` の直接呼び出しがないか走査する。
   ```bash
   grep -rnE "\b(alert|confirm|prompt)\(" frontend/ src/
   ```
   - 共通モーダルやトースト等のUIコンポーネントに置き換える。
3. **モバイル表示の検証**:
   - 画面幅375pxで意図しない横スクロール（bodyの幅超過）が発生していないかをテスト・検証する。

### 3. インフラ・コンテナの検査
コンテナ起動遅延やビルド肥大化を防止します。

1. **起動時処理の軽量化確認**:
   - Webアプリの起動シーケンス（ヘルスチェック通過前）に、全件DBスキャンや重い行列計算が含まれていないことを確認する。5秒以内に起動完了すること。
2. **コンテナビルド対象の確認 (.dockerignore)**:
   - キャッシュディレクトリ、生データ、不要なスクリプトがビルドコンテキストに含まれていないか確認する。
   ```bash
   # .dockerignore の除外漏れ確認
   git ls-files -i --exclude-from=.dockerignore
   ```
3. **SQLite等の並行書き込み防止**:
   - 分散コンテナ（Cloud Run等）からネットワークストレージ上の単一SQLiteへの一括書き込み処理がないか確認し、バッチ専用基盤に分離する。
