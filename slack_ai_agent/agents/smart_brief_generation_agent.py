import datetime
import json
import operator
import os
from dataclasses import field
from typing import Annotated
from typing import List
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from openai import OpenAI
from pydantic import BaseModel
from pydantic import Field

from slack_ai_agent.agents.tools.firecrawl_scrape import firecrawl_scrape
from slack_ai_agent.agents.tools.tavily_search import tavily_search


class ReportStateInput(TypedDict):
    url: str  # URL of the web content to analyze


class InputContent(BaseModel):
    url: str
    title: str
    markdown: str
    metadata: dict


class SearchQuery(BaseModel):
    query: str = Field(..., description="Query for web search.")
    aspect: str = Field(
        ..., description="Specific aspect of the topic being researched."
    )
    rationale: str = Field(
        ..., description="Brief explanation of why this query is relevant."
    )


class Section(BaseModel):
    headline: str = Field(
        description="Headline (小見出し) for this section of the article.",
    )
    content: str = Field(description="The content of the section.")
    quotes: List[dict] = Field(
        default_factory=list,
        description="Notable quotes from sources related to this section, with text, source, and relevance.",
    )


class ReportState(BaseModel):
    input: InputContent
    queries: list[SearchQuery]
    web_research_results: Annotated[list, operator.add] = field(default_factory=list)
    title: str
    micro: str
    tldr: str
    sections: list[Section]
    references: list[dict]


def fetch_url_content(url: str) -> dict:
    """
    Firecrawl APIを使ってURLから構造化コンテンツを取得する
    Returns:
        dict: {
            "title": str,
            "markdown": str,
            "metadata": dict
        }
    """
    try:
        result = firecrawl_scrape(url=url)
        markdown = result.get("markdown", "")
        metadata = result.get("metadata", {})
        title = metadata.get("title", "No title")
        return {"title": title, "markdown": markdown, "metadata": metadata}
    except Exception as e:
        print(f"Error fetching URL content: {str(e)}")
        return {
            "title": f"Error fetching content from {url}: {str(e)}",
            "markdown": "",
            "metadata": {},
        }


def preprocess_url(state: ReportStateInput) -> ReportState:
    """
    URLからコンテンツを取得し、初期状態を設定する
    """
    url = state["url"]
    url_content = fetch_url_content(url)

    return ReportState(
        input=InputContent(
            url=url,
            title=url_content["title"],
            markdown=url_content["markdown"],
            metadata=url_content["metadata"],
        ),
        queries=[],
        title="",
        micro="",
        tldr="",
        sections=[],
        references=[],
    )


def generate_query(state: ReportState) -> ReportState:
    """Generate a query for web search"""

    current_date = datetime.datetime.now().strftime("%Y年%m月%d日")

    # Format the prompt
    QUERY_INSTRUCTIONS = """
あなたの目標は、特定の記事内容に基づき、Tavily APIで高精度な事実検索ができるような具体的かつ明確な検索クエリを4つ以上生成することです。

- クエリは曖昧な表現や一般論を避け、できるだけ「事実」「データ」「比較」「最新動向」「根拠」「事例」「専門家の見解」「予測」などを明確に問う内容にしてください。
- Tavily APIは、明確な質問文や具体的な情報要求に対して最も有用な回答を返します。
- 例：Who/What/When/Where/Why/How で始まる具体的な質問や、数値・統計・比較・時系列・根拠・出典などを意識してください。
- 異なる視点や立場からの情報も収集できるよう、複数の角度からクエリを設計してください。
- 最新の情報を優先的に取得できるよう、現在の日付「{current_date}」を意識したクエリも含めてください。

<CONTENT>
{content}
</CONTENT>

<FORMAT>
4つ以上の検索クエリを配列形式のJSONで提供してください。各クエリは以下の3つのキーを持つオブジェクトとしてください:
- "query": Tavily APIで直接利用できる、明確かつ具体的な検索クエリ（例：「2025年の生成AI市場規模は？」「TransformerモデルとRNNの違い」「ChatGPTの主な活用事例（日本国内）」など）
- "aspect": そのクエリが調査するトピックの側面や観点（例：「市場動向」「技術比較」「実用事例」「専門家の見解」「将来予測」「課題と解決策」など）
- "rationale": なぜこのクエリが重要か、どのような知見が得られるかの簡単な説明（読者の関心を引くポイントも意識してください）
</FORMAT>

<EXAMPLE>
出力例：
[
  {{
    "query": "2025年の生成AI市場規模は？",
    "aspect": "市場動向・統計",
    "rationale": "最新の市場規模データを把握し、業界の成長性を評価するため"
  }},
  {{
    "query": "TransformerモデルとRNNの違い",
    "aspect": "技術比較",
    "rationale": "主要なAIモデルの特徴と利点・欠点を比較するため"
  }},
  {{
    "query": "ChatGPTの主な活用事例（日本国内）",
    "aspect": "実用事例",
    "rationale": "日本国内での具体的な活用例を知り、応用可能性を検討するため"
  }},
  {{
    "query": "AIに関する最新の倫理的議論と規制動向",
    "aspect": "倫理・規制",
    "rationale": "AI技術の社会実装における課題と対応策を理解するため"
  }},
  {{
    "query": "生成AI導入による企業の生産性向上 具体的な数値",
    "aspect": "ビジネス効果",
    "rationale": "投資対効果を定量的に評価し、導入判断の参考にするため"
  }}
]
</EXAMPLE>

JSON形式で4つ以上のクエリを配列として提供してください:
    """

    query_instructions_formatted = QUERY_INSTRUCTIONS.format(
        content=state.input.markdown, current_date=current_date
    )

    function_schema = {
        "name": "generate_query",
        "description": "Generate a query for web search",
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "aspect": {"type": "string"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["query", "aspect", "rationale"],
                    },
                    "description": "List of search queries",
                }
            },
            "required": ["queries"],
        },
    }

    # OpenAI APIクライアントを初期化
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    response = client.chat.completions.create(  # type: ignore[call-overload]
        model="gpt-4o-mini",
        temperature=0.1,
        max_completion_tokens=32_768,
        messages=[
            {"role": "system", "content": query_instructions_formatted},
            {
                "role": "user",
                "content": "提供されたコンテンツに基づいて、4つ以上の検索クエリを生成してください。",
            },
        ],
        tools=[{"type": "function", "function": function_schema}],
        tool_choice={"type": "function", "function": {"name": "generate_query"}},
    )

    # レスポンスから関数呼び出しの結果を取得
    function_call = response.choices[0].message.tool_calls[0]
    function_args = json.loads(function_call.function.arguments)

    # 関数呼び出しの結果を返す
    return ReportState(
        input=state.input,
        queries=function_args["queries"],
        title=state.title,
        micro=state.micro,
        tldr=state.tldr,
        sections=state.sections,
        references=state.references,
    )


def web_research(state: ReportState) -> ReportState:
    """state.queries の各 query でTavily APIを使ってウェブ検索を行い、結果をまとめる"""

    # state.queries は SearchQuery 型のリスト
    # 各 query フィールドを抽出してリスト化
    query_list = [q.query for q in state.queries if q.query]
    if not query_list:
        all_search_results = []
    else:
        all_search_results = tavily_search(query_list)

    return ReportState(
        input=state.input,
        queries=state.queries,
        web_research_results=all_search_results,
        title=state.title,
        micro=state.micro,
        tldr=state.tldr,
        sections=state.sections,
        references=state.references,
    )


def summarize_sources(state: ReportState) -> ReportState:
    """
    web_research_results をもとに、各検索結果から
    [
        {
            "headline": ...,
            "content": ...,
            "quotes": [
                {"text": ..., "source": ..., "url": ...},
                ...
            ]
        },
        ...
    ]
    の配列を返す。
    """

    # function_schemaに準拠したセクションを生成するためのプロンプト
    SECTION_GEN_PROMPT = """
あなたは調査レポートの自動要約AIです。
与えられたWeb検索結果（複数）をもとに、以下のJSONスキーマに従い、全体として「起承転結」の構成となるように各セクションを日本語で生成してください。

# スキーマ
{schema}

# 入力データ
{input_data}

# 制約
- sections全体で「起（導入）」「承（展開）」「転（転換・新たな視点）」「結（まとめ・示唆）」の流れを意識し、ユーザーが知識を理解・定着できるように構成してください。
- headline: 新聞社の見出しのように短く情報が詰まったタイトル（日本語で40字以内、装飾なし、マークダウン記法「# 」などは使用しない）
- content: セクションの役割に応じて、概要だけでなく具体的な内容も含めて本文を記述してください（300〜600文字程度、例：起は短め、承・転は詳細、結はまとめや示唆を強調）。
- quotes: 関連する重要な引用（最大3件、引用文は80字以内、必要に応じて省略可）
- references: 参照情報源（1〜3件、titleは80字以内、metadataはauthor/publishedDateが判明している場合のみ記載、内容に応じて適切な数を選択）

# 出力形式
- セクション数は必ず4つ以上としてください。
各セクションを配列形式のJSONで返してください。
    """

    # function_schemaのJSON文字列
    function_schema = {
        "name": "generate_sections",
        "description": "Generate an array of sections for a report. Each section contains headline, content, quotes, and references. Also generate overall title, micro, and tldr.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "レポート全体のタイトル（40字以内、新聞社の見出しのように短く情報が詰まったもの）",
                },
                "micro": {
                    "type": "string",
                    "description": "読む価値があるかを判定できる内容（100字以内、読者の興味を引く要点や独自性を強調）",
                },
                "tldr": {
                    "type": "string",
                    "description": "本文を読まずに知識を獲得できる140字以内の要約",
                },
                "references": {
                    "type": "array",
                    "description": "レポート全体の参照情報源（1〜10件、titleは80字以内、metadataはauthor/publishedDateが判明している場合のみ記載）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "参照タイトル（80字以内）",
                            },
                            "url": {
                                "type": "string",
                                "description": "参照元のURL（完全な形式）",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "参照に関する追加メタデータ",
                                "properties": {
                                    "author": {
                                        "type": "string",
                                        "description": "著者名（判明している場合のみ）",
                                    },
                                    "publishedDate": {
                                        "type": "string",
                                        "description": "発行日（YYYY-MM-DD形式、判明している場合のみ）",
                                    },
                                },
                            },
                        },
                        "required": ["title", "url"],
                    },
                },
                "sections": {
                    "type": "array",
                    "description": "レポートの各セクション（4つ以上）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {
                                "type": "string",
                                "description": "新聞社の見出しのように短く情報が詰まったタイトル（日本語で40字以内、装飾なし、マークダウン記法「# 」などは使用しない）",
                            },
                            "content": {
                                "type": "string",
                                "description": "本文（セクションの役割に応じて、概要だけでなく具体的な内容も含めて本文を記述してください（300〜600文字程度、例：起は短め、承・転は詳細、結はまとめや示唆を強調））",
                            },
                            "quotes": {
                                "type": "array",
                                "description": "関連する重要な引用（最大3件、引用文は80字以内、必要に応じて省略可）",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {
                                            "type": "string",
                                            "description": "引用文（80字以内）",
                                        },
                                        "source": {
                                            "type": "string",
                                            "description": "出典（例: レポート名、記事タイトルなど）",
                                        },
                                        "url": {
                                            "type": "string",
                                            "description": "参照元のURL（完全な形式）",
                                        },
                                    },
                                    "required": ["text", "source", "url"],
                                },
                            },
                        },
                        "required": ["headline", "content", "quotes"],
                    },
                },
            },
            "required": ["title", "micro", "tldr", "sections"],
        },
    }

    # 検索結果を文字列化
    input_data = json.dumps(state.web_research_results, ensure_ascii=False, indent=2)
    schema_str = json.dumps(function_schema["parameters"], ensure_ascii=False, indent=2)

    prompt = SECTION_GEN_PROMPT.format(schema=schema_str, input_data=input_data)

    # LLMでセクション配列を生成
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    response = client.chat.completions.create(  # type: ignore[call-overload]
        model="gpt-4o-mini",
        temperature=0.1,
        max_completion_tokens=32_768,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "上記の指示に従い、4つ以上のセクションを配列形式のJSONで出力してください。",
            },
        ],
        tools=[{"type": "function", "function": function_schema}],
        tool_choice={"type": "function", "function": {"name": "generate_sections"}},
    )

    print(response)
    function_call = response.choices[0].message.tool_calls[0]
    function_args = json.loads(function_call.function.arguments)

    references = function_args.get("references", [])

    return ReportState(
        input=state.input,
        queries=state.queries,
        web_research_results=state.web_research_results,
        title=function_args.get("title", getattr(state, "title", "")),
        micro=function_args.get("micro", getattr(state, "micro", "")),
        tldr=function_args.get("tldr", getattr(state, "tldr", "")),
        sections=function_args["sections"],
        references=references,
    )


builder = StateGraph(ReportState, input=ReportStateInput, output=ReportState)
builder.set_entry_point("preprocess_url")
builder.add_node("preprocess_url", preprocess_url)
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("summarize_sources", summarize_sources)

builder.add_edge(START, "preprocess_url")
builder.add_edge("preprocess_url", "generate_query")
builder.add_edge("generate_query", "web_research")
builder.add_edge("web_research", "summarize_sources")
builder.add_edge("summarize_sources", END)

graph = builder.compile()
