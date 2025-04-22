"""スマートブリーフ（朝刊・夕刊）生成エージェント

ユーザーが保存した複数のURLから記事情報を取得し、「朝刊」または「夕刊」形式のスマートブリーフを生成する。

PEP8/GoogleスタイルDocstring準拠
"""

from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph
from pydantic import BaseModel
from pydantic import Field


class EditionType(str, Enum):
    """朝刊・夕刊の区分"""

    MORNING = "morning"  # 朝刊
    EVENING = "evening"  # 夕刊


class Article(BaseModel):
    """単一記事のデータ構造"""

    url: str
    title: str
    content: str
    excerpt: str
    saved_at: datetime = Field(default_factory=datetime.now)
    category: Optional[str] = None
    read_status: bool = False


class ThemeCluster(BaseModel):
    """クラスタリング結果（テーマ単位のグループ）"""

    articles: List[Article]
    theme_name: str
    categories: List[str]
    summary: str = ""
    content: str = ""
    sources: List[Dict[str, str]] = []
    importance_score: float = 0.0  # ユーザー関心度に基づく重要度スコア


class SmartBrief(BaseModel):
    """スマートブリーフ（朝刊・夕刊）の出力構造"""

    edition_type: EditionType
    articleIds: List[str]
    categories: List[str]
    createdAt: datetime
    date: datetime
    title: str  # 例: "4月17日の朝刊"
    theme_name: str  # テーマ名
    summary: str  # テーマの要約
    content: str  # テーマの詳細内容
    importance_score: float = 0.0  # 重要度スコア
    sources: List[Dict[str, str]] = []  # 関連情報ソース
    theme: Optional[ThemeCluster] = None  # 元となるテーマクラスタ


# LangGraph用の状態管理クラス
class SmartBriefState(BaseModel):
    urls: List[str]
    edition_type: EditionType
    user_id: str
    user_preferences: Optional[Dict[str, float]] = None  # カテゴリ別関心度
    articles: Optional[List[Article]] = None
    clusters: Optional[List[ThemeCluster]] = None
    smartbriefs: Optional[List[SmartBrief]] = None


class SmartBriefInput(BaseModel):
    urls: List[str]
    edition_type: EditionType
    user_id: str
    user_preferences: Optional[Dict[str, float]] = None


class SmartBriefOutput(BaseModel):
    smartbriefs: List[SmartBrief]


# LangGraphノード関数
def fetch_url_contents_node(state: SmartBriefState, config=None):
    """URLリストから記事情報を取得しstate.articlesに格納"""
    agent = SmartBriefAgent()
    articles = agent.fetch_url_contents(state.urls)
    return {**state.dict(), "articles": articles}


def cluster_articles_node(state: SmartBriefState, config=None):
    """記事リストをクラスタリングしstate.clustersに格納"""
    agent = SmartBriefAgent()
    clusters = agent.cluster_articles(state.articles or [])
    return {**state.dict(), "clusters": clusters}


def analyze_user_interests_node(state: SmartBriefState, config=None):
    """ユーザーの興味関心に基づいてクラスタの重要度を算出"""
    agent = SmartBriefAgent()
    clusters = agent.analyze_user_interests(
        state.clusters or [], state.user_id, state.user_preferences or {}
    )
    return {**state.dict(), "clusters": clusters}


def llm_generate_brief_content_node(state: SmartBriefState, config=None):
    """LLMを使用してスマートブリーフコンテンツを生成"""
    import logging

    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage
    from langchain_core.messages import SystemMessage

    logger = logging.getLogger(__name__)
    clusters = state.clusters or []
    now = datetime.now()
    edition_type = state.edition_type
    edition_name = "朝刊" if edition_type == EditionType.MORNING else "夕刊"
    date_str = now.strftime("%Y年%m月%d日")
    title_base = f"{date_str}の{edition_name}"

    # LLMを初期化
    llm = init_chat_model(model="gpt-4", model_provider="openai", temperature=0.2)

    # 各テーマごとにスマートブリーフを生成
    smartbriefs = []

    for cluster in clusters:
        # テーマごとのLLMプロンプト
        theme_prompt = f"""あなたはNewsLaterアプリの「スマートブリーフ」機能を担当するAIアシスタントです。
ユーザーが保存した記事から、価値ある要約と関連情報をまとめた{edition_name}のテーマ記事を生成します。

## 入力データ
以下のテーマに関する記事情報があります：

テーマ名: {cluster.theme_name}
カテゴリ: {", ".join(cluster.categories)}
記事: {[{"title": a.title, "excerpt": a.excerpt} for a in cluster.articles]}

## 出力目標
このテーマの記事を分析し、以下の要素を含む構造化された記事を生成してください：

1. **要約**: テーマの重要ポイントを簡潔にまとめる（150-200字）
2. **詳細内容**: テーマの詳細情報（400-600字）

## スタイルとトーン
- 簡潔で明瞭な文章
- 新聞記事のような客観的なトーン
- 専門用語は必要に応じて説明を追加
- 日本語で出力

## 出力形式
以下のJSON形式で出力してください：
```json
{{
  "summary": "テーマの要約",
  "content": "テーマの詳細内容"
}}
```

## 制約条件
- 元の記事の著作権を尊重し、直接的な引用は避ける
- 事実確認が難しい内容については推測を避ける
"""

        try:
            # LLM呼び出し
            response = llm.invoke(
                [
                    SystemMessage(content=theme_prompt),
                    HumanMessage(
                        content=f"{cluster.theme_name}に関するスマートブリーフを生成してください"
                    ),
                ]
            )

            # 出力パース
            import json

            theme_content = {}

            if hasattr(response, "content") and isinstance(response.content, str):
                try:
                    # JSON文字列の抽出（```json〜```の間）
                    import re

                    json_match = re.search(
                        r"```json\s*([\s\S]*?)\s*```", response.content
                    )
                    if json_match:
                        theme_json = json_match.group(1)
                        theme_content = json.loads(theme_json)
                    else:
                        # JSON形式でない場合は直接ロード試行
                        theme_content = json.loads(response.content)
                except json.JSONDecodeError:
                    logger.error(f"JSON解析エラー: {cluster.theme_name}")
                    # フォールバック
                    theme_content = {
                        "summary": f"{cluster.theme_name}に関する要約",
                        "content": f"{cluster.theme_name}に関する詳細内容",
                    }
        except Exception as e:
            logger.error(f"LLM処理エラー: {str(e)}")
            theme_content = {
                "summary": f"{cluster.theme_name}に関する要約",
                "content": f"{cluster.theme_name}に関する詳細内容",
            }

        # 記事IDの生成
        articleIds = []
        for i, _ in enumerate(cluster.articles):
            articleIds.append(
                f"{edition_type.value}_article_{cluster.theme_name.replace(' ', '_')}_{i + 1}"
            )

        # スマートブリーフの生成
        smartbriefs.append(
            SmartBrief(
                edition_type=edition_type,
                articleIds=articleIds,
                categories=cluster.categories,
                createdAt=now,
                date=now,
                title=f"{title_base}: {cluster.theme_name}",
                theme_name=cluster.theme_name,
                summary=theme_content.get("summary", f"{cluster.theme_name}の要約"),
                content=theme_content.get("content", f"{cluster.theme_name}の詳細"),
                importance_score=cluster.importance_score,
                sources=cluster.sources,
                theme=cluster,
            )
        )

    # 重要度順にソート
    smartbriefs.sort(key=lambda x: x.importance_score, reverse=True)

    return {**state.dict(), "smartbriefs": smartbriefs}


def search_related_info_node(state: SmartBriefState, config=None):
    """各スマートブリーフに関連する追加情報を検索"""
    agent = SmartBriefAgent()
    smartbriefs = state.smartbriefs or []

    for smartbrief in smartbriefs:
        # テーマに関連する情報を検索（themeがNoneでない場合のみ）
        if smartbrief.theme is not None:
            theme_sources = agent.search_theme_related_info(
                smartbrief.theme, max_results=2
            )

            # 重複除去
            unique_sources = []
            urls = set()
            for source in theme_sources:
                if source.get("url") not in urls:
                    urls.add(source.get("url"))
                    unique_sources.append(source)

            # スマートブリーフのsourcesを更新
            smartbrief.sources.extend(unique_sources)

    return {**state.dict(), "smartbriefs": smartbriefs}


class SmartBriefAgent:
    """スマートブリーフ生成エージェント本体"""

    def fetch_url_contents(self, urls: List[str]) -> List[Article]:
        """指定URLリストから記事情報（タイトル・本文・抜粋）を取得する

        Args:
            urls (List[str]): 取得対象のURLリスト

        Returns:
            List[Article]: 取得した記事情報リスト
        """
        from slack_ai_agent.agents.tools.firecrawl_scrape import firecrawl_scrape

        articles: List[Article] = []
        for url in urls:
            try:
                result = firecrawl_scrape(url=url)
                content = result.get("content", "")
                metadata = result.get("metadata", {})
                title = metadata.get("title", "") if isinstance(metadata, dict) else ""
                excerpt = content[:100] if content else ""

                articles.append(
                    Article(
                        url=url,
                        title=title,
                        content=content,
                        excerpt=excerpt,
                        saved_at=datetime.now(),
                    )
                )
            except Exception:
                # エラー時は空データで埋める
                articles.append(
                    Article(
                        url=url,
                        title="",
                        content="",
                        excerpt="",
                        saved_at=datetime.now(),
                    )
                )
        return articles

    def cluster_articles(self, articles: List[Article]) -> List[ThemeCluster]:
        """記事リストを内容的に近いものでクラスタリングし、テーマごとにまとめる

        Args:
            articles (List[Article]): 記事情報リスト

        Returns:
            List[ThemeCluster]: テーマごとのクラスタリスト
        """
        # 実際の実装では、NLPを活用した本格的なクラスタリングアルゴリズムを使用
        if not articles:
            return []

        # 記事数が少ない場合は1クラスタにまとめる
        if len(articles) <= 3:
            theme_name = max(
                (a.title for a in articles if a.title),
                key=len,
                default="テーマ",
            )
            return [
                ThemeCluster(
                    articles=articles,
                    theme_name=theme_name,
                    categories=[],
                    importance_score=1.0,
                )
            ]

        # タイトルや内容の類似性に基づくシンプルなクラスタリング
        clusters: List[ThemeCluster] = []
        remaining_articles = list(articles)

        # 最大クラスタ数を決定（記事数に応じて調整）
        max_clusters = min(5, max(2, len(articles) // 2))

        for _ in range(max_clusters):
            if not remaining_articles:
                break

            seed_article = remaining_articles[0]
            cluster_articles = [seed_article]
            remaining_articles.remove(seed_article)

            # 関連記事の検索
            i = 0
            while i < len(remaining_articles):
                article = remaining_articles[i]
                # 類似度計算（単純な単語一致ベース）
                if self._calculate_similarity(seed_article, article) > 0.3:
                    cluster_articles.append(article)
                    remaining_articles.pop(i)
                else:
                    i += 1

            # テーマ名は最長または最新のタイトル
            theme_name = max(
                (a.title for a in cluster_articles if a.title),
                key=len,
                default="テーマ",
            )

            # カテゴリ推定（単純なルールベース）
            categories = self._estimate_categories(cluster_articles)

            clusters.append(
                ThemeCluster(
                    articles=cluster_articles,
                    theme_name=theme_name,
                    categories=categories,
                    importance_score=len(cluster_articles)
                    / len(articles),  # 単純な重要度計算
                )
            )

        # 残りの記事を最も類似度の高いクラスタに割り当て
        for article in remaining_articles:
            best_cluster_idx = -1
            best_similarity = 0.3  # 最低類似度閾値

            for idx, cluster in enumerate(clusters):
                for cluster_article in cluster.articles:
                    similarity = self._calculate_similarity(article, cluster_article)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_cluster_idx = idx

            if best_cluster_idx >= 0:
                # 既存クラスタに追加
                clusters[best_cluster_idx].articles.append(article)
            else:
                # 新規クラスタ作成
                clusters.append(
                    ThemeCluster(
                        articles=[article],
                        theme_name=article.title or "新規テーマ",
                        categories=self._estimate_categories([article]),
                        importance_score=1.0 / len(articles),
                    )
                )

        return clusters

    def _calculate_similarity(self, article1: Article, article2: Article) -> float:
        """2つの記事間の類似度を計算（0-1の値）"""
        # 実際の実装では、より高度なNLP手法（TF-IDF、単語埋め込みなど）を使用
        # ここではシンプルな単語一致に基づく類似度
        words1 = set((article1.title + " " + article1.excerpt).lower().split())
        words2 = set((article2.title + " " + article2.excerpt).lower().split())

        if not words1 or not words2:
            return 0

        common_words = words1.intersection(words2)
        return len(common_words) / max(len(words1), len(words2))

    def _estimate_categories(self, articles: List[Article]) -> List[str]:
        """記事群からカテゴリを推定"""
        # 実際の実装では、テキスト分類モデルなどを使用
        # ここではキーワードベースの単純な判定
        keywords = {
            "テクノロジー": ["AI", "技術", "開発", "IT", "アプリ", "デジタル"],
            "ビジネス": ["企業", "経営", "市場", "投資", "戦略", "経済"],
            "健康": ["健康", "医療", "ヘルスケア", "病院", "治療", "薬"],
            "科学": ["研究", "科学", "発見", "宇宙", "物理", "化学"],
            "エンタメ": ["映画", "音楽", "芸能", "テレビ", "ゲーム", "エンタメ"],
        }

        # すべての記事テキストを結合
        all_text = " ".join(
            [
                (a.title + " " + a.excerpt).lower()
                for a in articles
                if a.title or a.excerpt
            ]
        )

        # カテゴリごとにキーワード一致をカウント
        category_scores = {}
        for category, terms in keywords.items():
            score = sum(1 for term in terms if term.lower() in all_text)
            if score > 0:
                category_scores[category] = score

        # スコア順にソートして上位2つまで返す
        top_categories = sorted(
            category_scores.keys(), key=lambda k: category_scores[k], reverse=True
        )[:2]

        return top_categories or ["その他"]

    def analyze_user_interests(
        self,
        clusters: List[ThemeCluster],
        user_id: str,
        user_preferences: Optional[Dict[str, float]] = None,
    ) -> List[ThemeCluster]:
        """ユーザーの興味関心に基づいてクラスタの重要度を再計算

        Args:
            clusters: 記事クラスタのリスト
            user_id: ユーザーID
            user_preferences: カテゴリ別関心度辞書

        Returns:
            更新されたクラスタリスト
        """
        # ユーザー関心度がない場合は既存の重要度を使用
        if not user_preferences:
            return clusters

        # 各クラスタの重要度をユーザー関心度で調整
        for cluster in clusters:
            preference_boost = 1.0  # デフォルト倍率
            # カテゴリ別関心度に基づく調整
            for category in cluster.categories:
                if category in user_preferences:
                    preference_boost = max(preference_boost, user_preferences[category])

            # 重要度を更新
            cluster.importance_score *= preference_boost

        return clusters

    def search_theme_related_info(
        self, theme: ThemeCluster, max_results: int = 2
    ) -> List[Dict[str, str]]:
        """テーマに関連する追加情報をウェブ検索で取得

        Args:
            theme: テーマクラスタ
            max_results: 取得する検索結果数

        Returns:
            ソースリスト（title, excerpt, url）
        """
        from slack_ai_agent.agents.tools.tavily_search import tavily_search

        # 検索クエリはテーマ名＋記事タイトルを連結
        query = theme.theme_name
        if theme.articles:
            query += " " + " ".join([a.title for a in theme.articles if a.title])

        # 検索実行
        search_results = tavily_search(
            query=query, include_raw_content=False, max_results=max_results
        )
        sources = []
        if isinstance(search_results, dict) and "results" in search_results:
            for result in search_results["results"]:
                sources.append(
                    {
                        "title": result.get("title", ""),
                        "excerpt": result.get("content", ""),
                        "url": result.get("url", ""),
                    }
                )
        return sources


# LangGraph StateGraph定義
def build_smartbrief_graph():
    """LangGraph StateGraphを構築して返す"""
    builder = StateGraph(
        SmartBriefState,
        input=SmartBriefInput,
        output=SmartBriefOutput,
    )
    builder.add_node("fetch_url_contents", fetch_url_contents_node)
    builder.add_node("cluster_articles", cluster_articles_node)
    builder.add_node("analyze_user_interests", analyze_user_interests_node)
    builder.add_node("llm_generate_brief_content", llm_generate_brief_content_node)
    builder.add_node("search_related_info", search_related_info_node)

    # 出力変換ノードを追加
    def output_transform_node(state: SmartBriefState, config=None):
        return {"smartbriefs": state.smartbriefs or []}

    builder.add_node("output_transform", output_transform_node)

    builder.add_edge(START, "fetch_url_contents")
    builder.add_edge("fetch_url_contents", "cluster_articles")
    builder.add_edge("cluster_articles", "analyze_user_interests")
    builder.add_edge("analyze_user_interests", "llm_generate_brief_content")
    builder.add_edge("llm_generate_brief_content", "search_related_info")
    builder.add_edge("search_related_info", "output_transform")
    builder.add_edge("output_transform", END)

    return builder.compile()


graph = build_smartbrief_graph()
