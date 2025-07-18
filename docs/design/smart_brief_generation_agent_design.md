# smart_brief_generation_agent 設計書

## 要件定義

- 記事やWebページの内容から、関連するウェブ検索クエリを自動生成するエージェントを実装する。
- 生成される検索クエリは、記事内容の多面的な調査や要約に活用される。
- OpenAI APIを利用し、与えられたコンテンツから3つの検索クエリ（query, aspect, rationale）をJSON配列形式で出力する。

## 概略設計

- 入力：URLまたは記事コンテンツ
- 処理：
  - URLから記事内容を取得し、構造化データへ変換
  - 記事内容をもとに、OpenAI APIを用いて検索クエリを生成
  - 生成クエリはJSON配列形式で返却
- 出力：検索クエリリスト

## 機能設計

- `fetch_url_content(url: str)`: Firecrawl APIでURLから記事内容を取得
- `preprocess_url(state: ReportStateInput)`: URLから初期状態を生成
- `generate_query(state: ReportState)`: OpenAI APIで検索クエリを生成
  - プロンプトテンプレート内のリテラル波括弧 `{}` を `{{}}` へエスケープし、`str.format()` のKeyErrorを防止
- `web_research(state: ReportState)`: **Tavily API（tavily_search）を利用して、生成された検索クエリごとにWeb検索を実施し、結果を取得**
- `summarize_sources(state: ReportState)`:
  - Tavily検索結果をもとに、全体として「起承転結」構成となるような複数（3つ以上）のセクションを生成
  - 各セクションはheadline（新聞社の見出しのように短く情報が詰まったもの）、content（300〜600字、概要＋具体的内容）、quotes（最大3件、必要に応じて省略可）を持つ
  - references（参照情報源）は全体項目としてまとめる
  - レポート全体のtitle（40字以内）、micro（読む価値があるか判定できる内容、100字以内）、tldr（本文を読まずに知識を獲得できる140字以内）も生成
  - 生成物はReportStateのtitle, feedback_on_report_plan, report_sections_from_research, sections等に格納
- その他、要約・リフレクション等の補助関数

## クラス構成

- `ReportStateInput`, `ReportStateOutput`, `ReportState`, `InputContent`, `SearchQuery`, `Section` などのデータクラス
- メイン処理は `StateGraph` でノードとして管理

## 修正履歴

### 2025-04-27

- `generate_query` 内のプロンプトテンプレート（`QUERY_INSTRUCTIONS`）で、Pythonの `str.format()` によるKeyError（`KeyError: '\n    "query"'`）が発生。
  - 原因：テンプレート内のJSON例や説明文中の `{}` が `str.format()` の置換対象となっていたため。
  - 対応：`QUERY_INSTRUCTIONS` 内のリテラル `{}` を `{{}}` へエスケープし、`{content}` プレースホルダのみを残すよう修正。

#### 2025-04-27

- Webリサーチ処理で利用する外部APIを **Perplexity API** から **Tavily API（tavily_search）** へ再度切り替え。
  - 理由：Tavily APIの利用要件・仕様変更に対応するため。
  - `web_research` 関数で、各検索クエリをまとめてTavily APIに投げ、結果を取得する実装に変更。

#### 2025-04-28

- summarize_sourcesで生成するレポート構造を大幅に拡張
  - セクションは3つ以上、全体で「起承転結」構成
  - headlineは新聞社の見出しのように短く情報密度が高い
  - contentは300〜600字、概要＋具体的内容
  - referencesは全体項目としてまとめる
  - title, micro, tldr（要約）を全体項目として生成
  - これらをReportStateのtitle, feedback_on_report_plan, report_sections_from_research, sections等に格納
