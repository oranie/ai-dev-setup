# Antigravity 開発ガイドライン (GEMINI.md)

本リポジトリでは、Antigravity（Gemini）とClaude Codeの併用環境で開発を行います。
エージェント共通の行動指針および7大禁止事項については、必ず [AGENTS.md](./AGENTS.md) を最優先で遵守してください。

---

## 1. Antigravity固有の運用ルール

### 1-1. リファレンス先行（Reference-First）の徹底
- 新しい機能の実装、外部APIの連携、インフラ設定の変更を命じられた場合、いきなりコード生成を行わないこと。
- まず `reference-survey` スキルを活用し、公式ドキュメントやリポジトリの仕様を調査して `docs/references/` 配下にMarkdownで記録すること。
- 調査結果を元に実装計画（implementation_plan）を立て、確認した正確なシグネチャ・設定値のみを用いてコードを記述すること。

### 1-2. スキルと監査の実行
- 実装完了後は、以下の監査スキルを適宜実行して品質を担保すること。
  - `leak-and-wiring-audit`: データリーク（未来データ参照）やデータ配線抜けの監査
  - `code-quality-audit`: 形骸化テスト（アサーション抜け）、CSS `!important`、ブラウザ標準ダイアログの検出

### 1-3. トークン消費の最適化
- ターミナルでコマンドを実行する際、数千行に及ぶ大量の生ログをそのまま標準出力に出さないこと。`grep`, `head`, `tail`, `jq` 等を用いて必要な箇所に絞り込んで確認すること。
- スクラッチスクリプトを作成して検証を行う場合は、ワークスペースを汚さず `.gemini/antigravity/brain/<conversation-id>/scratch/` または `scripts/scratch/` を使用すること。

### 1-4. Git操作の安全ルール
- ステージング時は `git add -A` や `git add .` を使用せず、変更したファイルパスを明示して実行すること。
- `.agents/hooks.json` にて危険コマンドの抑止フックが設定されているため、フックの指示に従うこと。
