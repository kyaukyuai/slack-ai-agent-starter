# スマートブリーフ（朝刊・夕刊）生成エージェント設計書

## 1. 要件定義

### 目的
ユーザーが保存した複数のURLからコンテンツを取得し、その内容をもとに自動的に複数の「テーマ」を抽出。各テーマごとに「朝刊」または「夕刊」形式のスマートブリーフ（カテゴリ、記事ID、sources、summary等）を生成する。ユーザーの興味関心に基づいて重要度を調整し、より価値のある情報を提供する。

### 機能要件
- ユーザーが指定した複数のURLからWebページの内容（タイトル・本文）を取得する
- 取得した内容をもとに、内容的に近いものを自動でグルーピング（テーマ抽出/クラスタリング）
- ユーザーの興味関心（カテゴリ別関心度）に基づいてテーマの重要度を算出
- 朝刊・夕刊の区分に応じたスマートブリーフを生成
- 各テーマごとに
    - 記事IDリスト（articleIds）
    - カテゴリリスト（categories）
    - sources（各URLのタイトル・抜粋・URL）
    - summary（テーマ全体の要約）
    - content（テーマ全体の本文。summaryより詳細な内容）
    - importance_score（重要度スコア）
    - その他、スマートブリーフに必要な情報（作成日時、朝刊/夕刊区分等）
  を生成する
- 出力はJSONライクな構造体で返す

### 非機能要件
- PEP8/GoogleスタイルDocstring準拠
- テストコードをtests/agents/配下に作成
- 設計書をdocs/design/配下に作成

## 2. 概要設計

### 全体フロー
1. 入力：URLリスト、朝刊/夕刊区分、ユーザーID、ユーザー関心度
2. 各URLからタイトル・本文・抜粋を取得（firecrawl_scrape等を利用）
3. 取得した全記事をテキストベースでクラスタリング（類似度計算＋グルーピング）
4. ユーザーの興味関心に基づいてクラスタの重要度を算出
5. 各クラスタ（テーマ）ごとに
    - LLMを使用してスマートブリーフコンテンツを生成
    - sourcesリスト生成（title, excerpt, url）
    - テーマに関連する追加情報をウェブサーチ（tavily_searchを利用）
    - summary生成（テーマ全体の要約。ウェブサーチ結果も活用）
    - content生成（テーマ全体の本文。summaryより詳細な内容。ウェブサーチ結果も活用）
    - カテゴリ推定（例：健康、科学、経済など）
    - articleIds生成（ユニークなID）
    - その他メタ情報付与
6. スマートブリーフデータを返却

### クラス構成
- SmartBriefAgent（メインクラス）
    - fetch_url_contents(urls: List[str]) -> List[Article]
    - cluster_articles(articles: List[Article]) -> List[ThemeCluster]
    - analyze_user_interests(clusters: List[ThemeCluster], user_id: str, user_preferences: Optional[Dict[str, float]]) -> List[ThemeCluster]
    - search_theme_related_info(theme: ThemeCluster, max_results: int) -> List[dict]
- EditionType（朝刊・夕刊の区分）
    - MORNING: "morning"
    - EVENING: "evening"
- Article（URLごとの記事データ構造）
    - url, title, content, excerpt, saved_at, category, read_status
- ThemeCluster（クラスタリング結果：テーマ単位のグループ）
    - articles: List[Article]
    - theme_name: str
    - categories: List[str]
    - summary: str
    - content: str
    - sources: List[Dict[str, str]]
    - importance_score: float
- SmartBrief（最終出力構造）
    - edition_type: EditionType
    - articleIds: List[str]
    - categories: List[str]
    - createdAt: datetime
    - date: datetime
    - title: str
    - theme_name: str
    - summary: str
    - content: str
    - importance_score: float
    - sources: List[Dict[str, str]]
    - theme: Optional[ThemeCluster]

### 主要関数
- fetch_url_contents: firecrawl_scrapeでURLから記事情報を取得
- cluster_articles: 文章ベクトル化＋クラスタリング（単語一致ベースの類似度計算）
- analyze_user_interests: ユーザーの興味関心に基づいてクラスタの重要度を算出
- search_theme_related_info: テーマごとに追加のウェブサーチを行い、sourcesやsummary/content生成に活用
- llm_generate_brief_content: LLMを使用してスマートブリーフコンテンツを生成

## 3. 詳細設計

### データ構造

#### EditionType
```python
class EditionType(str, Enum):
    MORNING = "morning"  # 朝刊
    EVENING = "evening"  # 夕刊
```

#### Article
```python
class Article(BaseModel):
    url: str
    title: str
    content: str
    excerpt: str
    saved_at: datetime = Field(default_factory=datetime.now)
    category: Optional[str] = None
    read_status: bool = False
```

#### ThemeCluster
```python
class ThemeCluster(BaseModel):
    articles: List[Article]
    theme_name: str
    categories: List[str]
    summary: str = ""
    content: str = ""
    sources: List[Dict[str, str]] = []
    importance_score: float = 0.0  # ユーザー関心度に基づく重要度スコア
```

#### SmartBrief
```python
class SmartBrief(BaseModel):
    edition_type: EditionType
    articleIds: List[str]
    categories: List[str]
    createdAt: datetime
    date: datetime
    title: str  # 例: "4月17日の朝刊: テーマ名"
    theme_name: str  # テーマ名
    summary: str  # テーマの要約
    content: str  # テーマの詳細内容
    importance_score: float = 0.0  # 重要度スコア
    sources: List[Dict[str, str]] = []  # 関連情報ソース
    theme: Optional[ThemeCluster] = None  # 元となるテーマクラスタ
```

### 入出力例

#### 入力
```python
{
    "urls": [
        "https://example.com/health-science-journal",
        "https://example.com/modern-health-guide",
        ...
    ],
    "edition_type": "morning",
    "user_id": "user123",
    "user_preferences": {
        "健康": 1.5,
        "科学": 1.2,
        "ビジネス": 0.8
    }
}
```

#### 出力
```python
{
    "smartbriefs": [
        {
            "edition_type": "morning",
            "articleIds": ["morning_article_health_research_1", "morning_article_health_research_2"],
            "categories": ["健康", "科学"],
            "createdAt": "2025-04-22T09:25:52+09:00",
            "date": "2025-04-22T09:25:52+09:00",
            "title": "2025年4月22日の朝刊: 最新の健康研究が示す運動の重要性",
            "theme_name": "最新の健康研究が示す運動の重要性",
            "summary": "最新の健康研究によると、1日わずか15分の軽い運動でも、寿命を延ばす効果があることが明らかになりました。...",
            "content": "10年間にわたる大規模調査の結果、1日15分の軽い運動が健康寿命を延ばすことが明らかになった。研究では5万人以上を追跡し、運動の継続性が重要であることが示された。...",
            "importance_score": 1.5,
            "sources": [...]
        },
        {
            "edition_type": "morning",
            "articleIds": ["morning_article_tech_innovation_1"],
            "categories": ["テクノロジー", "ビジネス"],
            "createdAt": "2025-04-22T09:25:52+09:00",
            "date": "2025-04-22T09:25:52+09:00",
            "title": "2025年4月22日の朝刊: 最新テクノロジーの動向",
            "theme_name": "最新テクノロジーの動向",
            "summary": "AIと量子コンピューティングの融合が新たな技術革新をもたらしています...",
            "content": "大手テクノロジー企業が次世代AI技術と量子コンピューティングを組み合わせた新しいプラットフォームを発表...",
            "importance_score": 1.2,
            "sources": [...]
        }
    ]
}
```

### アルゴリズム概要

- URLごとにfirecrawl_scrapeで記事情報を取得
- 取得した記事を単語一致ベースの類似度計算でクラスタリング
- ユーザーの興味関心（カテゴリ別関心度）に基づいてクラスタの重要度を算出
- 各クラスタごとに独立したスマートブリーフを生成
    - LLMでテーマごとのスマートブリーフコンテンツを生成
    - テーマ名・カテゴリ・summary・contentを生成
    - sourcesリストを作成
    - 必要に応じてtavily_searchで追加情報を取得し、summary/content生成に活用
    - articleIdsは"morning_article_{theme_name}_{n}"または"evening_article_{theme_name}_{n}"で生成
    - createdAt/dateは実行時刻
    - edition_typeは入力パラメータで指定
- 重要度スコアの高い順にスマートブリーフをソート

## 4. テスト方針

- fetch_url_contents: モックでURL→Article取得のテスト
- cluster_articles: サンプル記事でクラスタ数・内容の妥当性テスト
- analyze_user_interests: ユーザー関心度に基づく重要度算出のテスト
- search_theme_related_info: テーマごとの追加情報取得のテスト
- llm_generate_brief_content: LLMによるコンテンツ生成のテスト
