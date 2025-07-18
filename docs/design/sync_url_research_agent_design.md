# sync_url_research_agent 構造化設計書

## 要件定義

- URLから取得した情報を「記事」として扱いやすいように、title（タイトル）、sections（セクション）などの構造化データとして出力する。
- 各セクションは、headline（小見出し）、content（本文）、quotes（引用）、references（参考文献）を持つ。
- 記事全体の title（タイトル）を持つ。
- URLコンテンツを構造化された形式（InputContent）で保持する。
- 検索クエリ（queries）を独立したステップで生成する。
- 最終出力（compile_final_report）は headline, sections などを含むJSON形式とする。

## 概略設計

- Section クラスに headline（小見出し）フィールドを追加。
- InputContent クラスを新設し、URL情報を構造化（url, title, markdown, metadata）。
- ReportState で記事全体の title（タイトル）と input（InputContent）、queries（検索クエリ）を保持。
- generate_report_queries を独立したグラフノードとして実装。
- compile_final_report で title, sections（各セクションのheadline, content, quotes, references）を持つJSONを生成。
- write_section, write_final_sections で headline, content, quotes, references を生成・格納。
- format_sections などの補助関数も headline, section 構造に対応。

## 機能設計

- URLから構造化情報取得（fetch_url_content）- firecrawl_scrape APIを使用
- 検索クエリ生成（generate_report_queries）
- レポートプラン生成（generate_report_plan）
- セクションごとのリサーチ・生成（write_section, write_final_sections）
- 記事構造での最終出力（compile_final_report）
- 要約生成（micro, digest, deep）

## クラス構成

- InputContent (BaseModel)
  - url: str
  - title: str
  - markdown: str
  - metadata: dict

- Section (BaseModel)
  - headline: str  # 小見出し
  - description: str  # 概要
  - research: bool  # リサーチ要否
  - content: str   # 本文
  - quotes: List[dict]  # 重要な引用（text, source, relevanceを含む）
  - references: List[Dict]  # 参考文献（title, url, metadataを含む）

- Sections (BaseModel)
  - sections: List[Section]

- ReportState (TypedDict)
  - input: InputContent  # 入力情報を構造化
  - queries: list[SearchQuery]  # 検索クエリリスト
  - title: str  # 記事全体のタイトル
  - sections: list[Section]  # セクションリスト
  - completed_sections: list  # 完了したセクション
  - report_sections_from_research: str  # リサーチ結果
  - final_report: str  # 最終レポート

## 処理フロー

1. preprocess_url: URLからコンテンツを取得し、InputContentとして構造化
2. generate_report_queries: 検索クエリを生成
3. generate_report_plan: レポートのセクション構成を計画
4. build_section_with_web_research: 各セクションのリサーチと執筆
5. gather_completed_sections: 完了したセクションの収集
6. write_final_sections: 最終セクションの執筆
7. compile_final_report: 最終レポートのJSON生成（要約生成を含む）

## 要約生成プロンプト

記事の要約は以下のプロンプトを使用してLLMで生成します：

### micro（短い要約）
```
あなたは上級編集者です。
以下の記事本文を60～80字の1文で要約してください。
記事: """${content}"""
```

### digest（3行要約）
```
以下の記事を3行で要約し、日本語50字以内/行で出力。
返却形式:
1) 行1
2) 行2
3) 行3
記事: """${content}"""
```

### deep（詳細要約）
```
JSON形式で以下項目を生成:
{
 "tl;dr": "100字以内要約",
 "bullets": ["30字以内×3"],
 "quote": "最も示唆的な一文"
}
記事: """${content}"""
```

## 出力形式

```json
{
  "input": {
    "url": "https://example.com",
    "title": "ページタイトル",
    "markdown": "マークダウン形式のコンテンツ...",
    "metadata": {
      "og:title": "OGタイトル",
      "description": "ページの説明..."
    },
  },
  "title": "記事タイトル",
  "image_url": "",
  "micro": "短い要約...",
  "digest": ["要点1", "要点2", "要点3"],
  "importance": 0.85,
  "sections": [
    {
      "headline": "セクション1",
      "content": "本文...",
      "quotes": [
        {
          "text": "重要な引用1",
          "source": "引用元1",
          "relevance": 0.9
        },
        {
          "text": "重要な引用2",
          "source": "引用元2",
          "relevance": 0.8
        }
      ],
      "references": [
        {
          "title": "参考文献1のタイトル",
          "url": "https://example.com/reference1",
          "metadata": {"author": "著者名", "published_date": "2025-04-20"}
        },
        {
          "title": "参考文献2のタイトル",
          "url": "https://example.com/reference2",
          "metadata": {"author": "著者名", "published_date": "2025-04-21"}
        }
      ]
    },
    {
      "headline": "セクション2",
      "content": "本文...",
      "quotes": [
        {
          "text": "重要な引用3",
          "source": "引用元3",
          "relevance": 0.85
        },
        {
          "text": "重要な引用4",
          "source": "引用元4",
          "relevance": 0.75
        }
      ],
      "references": [
        {
          "title": "参考文献3のタイトル",
          "url": "https://example.com/reference3",
          "metadata": {"author": "著者名", "published_date": "2025-04-22"}
        },
        {
          "title": "参考文献4のタイトル",
          "url": "https://example.com/reference4",
          "metadata": {"publisher": "出版社名"}
        }
      ]
    }
  ],
  "readState": "unread",
  "estimatedMinutes": 5,
  "createdAt": "2025-04-25T12:34:56Z"
}
```
