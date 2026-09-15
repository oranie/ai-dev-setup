---
name: reference-survey
description: >-
  Use this skill before writing or modifying code, infrastructure configurations, or external integrations.
  Searches official documentation, GitHub repositories, and reliable technical blogs to build and record
  verified references in docs/references/ before implementation.
---

# リファレンス先行調査スキル (reference-survey)

このスキルは、コードや設定ファイルを生成する前に、対象技術の公式マニュアル、公開リポジトリ、技術記事を調査して `docs/references/` に技術メモを蓄積する手順書です。

当てずっぽうな実装によるAPI呼び出しエラー、IAM権限不足（403）、存在しない設定パラメータの捏造、古い記法の混入を防ぎ、修正ループによるトークン浪費を抑止します。

---

## 調査手順

### 1. 調査対象の特定
タスクに着手する際、以下の要素を洗い出します。
- 使用するライブラリ・フレームワーク（バージョンを含む）
- 呼び出すAPIのエンドポイントやメソッド
- クラウドインフラ（Cloud Run, S3, IAMロール等）の設定項目
- 外部データソースのスキーマ・エンコーディング

### 2. リファレンスの収集
以下の優先順位で情報源を検索・取得します。

1. **公式ドキュメント**:
   - 仕様書、APIリファレンス、公式ガイド
2. **GitHubの公開リポジトリ**:
   - 公式SDKの実装、テストコード、利用例（exampleディレクトリ）
   - issues / PR（既知のバグや制約事項の確認）
3. **信頼できる技術ブログ・検証記事**:
   - 実際の運用事例、落とし穴、パフォーマンス特性

※ 検索時は、対象のライブラリ名、バージョン、具体的なエラーコードや設定名を含めて絞り込みます。

### 3. 技術メモの記録
収集した情報を元に、`docs/references/` 配下にMarkdownファイルを作成します。
テンプレート: [docs/references/template.md](../../../docs/references/template.md)

記録すべき必須項目:
- **公式ドキュメント・GitHubのURL**
- **正確な引数・戻り値の型・シグネチャ**
- **必要なIAM権限や環境変数**
- **既知のエラー条件や回避策**
- **最小動作コード例（MWE: Minimal Working Example）**

### 4. 計画への反映と実装開始
`docs/references/` に作成した技術メモを根拠として提示し、そこに記載された正確な仕様に基づいてコードや設定ファイルを生成します。
調査メモに存在しないパラメータや挙動を推測で書き足してはなりません。
