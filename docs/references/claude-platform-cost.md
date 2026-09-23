# Claude Platform のコスト削減とモデル移行 実装リファレンス

- 調査日: 2026-09-23
- 参照元URL:
  - 公式ブログ: https://claude.com/blog/reducing-cost-and-improving-performance-with-claude-platform
  - 公式ドキュメント（サブエージェント）: https://code.claude.com/docs/en/sub-agents
- 対象バージョン: Claude Opus 5.5（`claude-opus-5-5`）、Claude Code のサブエージェント frontmatter

## 1. 概要と採用理由

Opus 5.5 の公開に合わせて出た、コストを下げる 3 つの手段（プロンプトキャッシュ、指示の監査、effort の調整）。
このテンプレートのうち、`CLAUDE.md` 3 節の委譲と `.claude/agents/` に直接かかわる。

## 2. 正確な仕様・設定構文

### プロンプトキャッシュ（ブログ）

- 同じプレフィックスで始まるリクエストは、KV キャッシュを読み戻す。読み出しは入力の定価より安い
- effort や thinking の設定はプロンプトの前方に入るため、会話の途中で変えるとキャッシュが切れる。
  **例外: Opus 5 と Fable 5.1 は effort を途中で変えてもキャッシュが切れない**
- タイムスタンプや ID のような変わる値は、キャッシュするプレフィックスから外す
- **サブエージェントや分岐が親のキャッシュを共有するのは、同じモデルでプレフィックスがバイト単位で一致するときだけ**
- キャッシュの TTL より長く走る同期ツール呼び出しやサブエージェントは避ける。既定は 5 分、1 時間も選べる
- system prompt は途中で書き換えず、更新はメッセージとして足す
- 使用頻度の低いツールは `defer_loading` にする

### 指示の監査（ブログ）

外すべきアンチパターン:

- 「作業を見直せ」のような検算の儀式
- 「徹底的に」「CRITICAL: YOU MUST ALWAYS」のような強調。冗長な出力を招く
- 「スクラッチパッドで段階的に考えよ」のような固定手順・推論テンプレート
- 古いモデルの失敗に合わせた few-shot
- 矛盾した指示
- 廃止された設定値。Opus 4.8 から 5.5 への移行事例では、廃止された thinking 設定で全リクエストが拒否された

`/claude-api prompt-audit` で自動検出できる。移行事例では、アンチパターンを外してコストがさらに 9% 下がり、精度が約 2 ポイント上がった。

### effort の調整（ブログ）

- 「高いほど良い」は成り立たない。掘る証拠が残っている間しか熟考は効かない
- 強いモデルの低 effort が、弱いモデルの高 effort より安くて同等のことがある
  （Fable 5.1 の low が Fable 5 の high と同等で、コストは 3 分の 1。CursorBench 3.2）
- 自分のタスクで effort を振って測る。曲線が平らなら、思考量はボトルネックではない
- `/claude-api hillclimb` は train/test に分けて設定を探す。`/claude-api cost-optimize` はトークンの使い道を洗い出す

### サブエージェントの frontmatter（公式ドキュメント）

```yaml
model: claude-opus-5-5   # エイリアス（opus 等）、フル ID、inherit
effort: low              # low / medium / high / xhigh / max
experimental:
  cacheTtl: 1h           # 5m / 1h。Claude Code v2.1.248 以降
```

- thinking はサブエージェントごとには設定できない。本体の設定を継承する（v2.1.198 以降）

## 3. 必要な権限・前提条件

- `experimental.cacheTtl` は Claude Code v2.1.248 以降

## 4. 既知の落とし穴・注意点

- 委譲先は本体と別モデルなので、本体のキャッシュは使えない。委譲のたびに規約を定価で読む
- 長い委譲の間に本体のキャッシュが TTL で失効すると、戻ったあとのターンで全履歴を定価で読み直す
- セッション途中の `/model` 切り替えはキャッシュを切る

## 5. 本プロジェクトでの適用

| 対象 | 判断 | 理由 |
|---|---|---|
| `implementer` の `model:` | `claude-opus-5` → `claude-opus-5-5` | 最新の Opus へ |
| `CLAUDE.md` 3 節 | キャッシュの共有条件、TTL、`/model` 切り替えの注意を追記 | 委譲のコストの中身を書いていなかった |
| `CLAUDE.md` 2 節 | モデル移行時に `/claude-api prompt-audit` を回す一文を追記 | 移行時の定型作業 |
| `AGENTS.md` 冒頭 | 「2-A-6 のUI」→「2-B-2 のUI」 | 節番号が実体と食い違っていた（矛盾した指示） |
| `AGENTS.md` 4 節 | 「3点」→「4点」 | 項目は 4 つある |
| `AGENTS.md` の「必ず」 | 4 箇所を削除 | 強調の積み増し。文意は「すること」で足りる |
| agent の `effort:` | **入れない** | 測った数字が無い（AGENTS.md 2-A-8）。段階を振って測ってから決める |
| `experimental.cacheTtl` | **入れない** | 実験的な設定で、委譲 1 回の実行時間を測っていない |
| `AGENTS.md` 4 節 3 の「読み返す」 | **残す** | 見るもの（項目の取り違え、単位、重複）が具体的で、検算の儀式には当たらない |
