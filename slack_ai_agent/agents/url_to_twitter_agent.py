import os
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import TypedDict

from langchain.schema import HumanMessage
from langchain.schema import SystemMessage
from langchain_core.messages import AIMessage
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from slack_ai_agent.agents.tools.deep_research import deep_research
from slack_ai_agent.agents.tools.firecrawl_scrape import firecrawl_scrape
from slack_ai_agent.agents.utils.models import model


# URLToTwitterStateをTypeDict型として定義
class URLToTwitterState(TypedDict, total=False):
    """URLからTwitterへの投稿を行うエージェントの状態。

    Attributes:
        messages (List[BaseMessage]): 会話の履歴
        url (str): スクレイピングするURL
        user_id (Optional[str]): Twitter認証用のユーザーID
        scraped_content (str): スクレイピングした内容
        scraped_data (Dict): スクレイピング結果の生データ
        topic (str): 抽出されたトピック
        related_knowledge (str): トピックに関連する周辺知識
        tweet_content (str): 投稿内容
        tweet_result (str): 投稿結果
        error (str): エラーメッセージ
    """

    messages: List[BaseMessage]
    url: str
    user_id: Optional[str]
    scraped_content: str
    scraped_data: Dict
    topic: str
    related_knowledge: str
    tweet_content: str
    tweet_result: str
    error: str


def extract_url(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, str]:
    """会話からURLを抽出する。

    Args:
        state (Dict[str, Any]): 現在の状態
        config (RunnableConfig): ランタイム設定

    Returns:
        Dict[str, str]: 抽出したURLを含む辞書
    """
    messages = state["messages"]
    if not messages:
        return {"url": ""}

    # 最後のメッセージからURLを抽出
    last_message = messages[-1]

    # last_messageがBaseMessage型の場合
    if hasattr(last_message, "content"):
        message_content = last_message.content
        if not isinstance(message_content, str):
            return {"url": ""}
    # last_messageが辞書型の場合
    elif isinstance(last_message, dict) and "content" in last_message:
        message_content = last_message["content"]
        if not isinstance(message_content, str):
            return {"url": ""}
    else:
        return {"url": ""}

    # URLを抽出するためのプロンプト
    result = model.invoke(
        [
            SystemMessage(
                content="あなたはURLを抽出するアシスタントです。与えられたテキストからURLを抽出してください。"
            ),
            HumanMessage(
                content=f"以下のテキストからURLを抽出してください:\n{message_content}"
            ),
        ]
    )

    if isinstance(result.content, str):
        # 簡易的なURL抽出
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, result.content)
        if urls:
            return {"url": urls[0]}

    return {"url": ""}


def scrape_url(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """URLの内容をスクレイピングする。

    Args:
        state (Dict[str, Any]): 現在の状態
        config (RunnableConfig): ランタイム設定

    Returns:
        Dict[str, Any]: スクレイピング結果を含む辞書
    """
    url = state.get("url", "")

    if not url:
        # URLが空の場合はエラーメッセージを追加
        state["messages"].append(
            AIMessage(
                content="URLが見つかりませんでした。有効なURLを入力してください。"
            )
        )
        return state

    try:
        # URLをスクレイピング
        scraped_data = firecrawl_scrape(url=url)

        # スクレイピングした内容を抽出
        if isinstance(scraped_data, dict) and "content" in scraped_data:
            content = scraped_data["content"]
        else:
            content = str(scraped_data)

        return {
            "scraped_content": content,
            "scraped_data": scraped_data,
        }
    except Exception as e:
        # エラーが発生した場合はエラーメッセージを追加
        state["messages"].append(
            AIMessage(content=f"スクレイピング中にエラーが発生しました: {str(e)}")
        )
        return state


def extract_topic_and_research(
    state: Dict[str, Any], config: RunnableConfig
) -> Dict[str, str]:
    """スクレイピング結果からトピックを抽出し、関連する周辺知識を取得する。

    Args:
        state (Dict[str, Any]): 現在の状態
        config (RunnableConfig): ランタイム設定

    Returns:
        Dict[str, str]: トピックと関連知識を含む辞書
    """
    scraped_content = state.get("scraped_content", "")
    scraped_data = state.get("scraped_data", {})

    if not scraped_content:
        # スクレイピングした内容がない場合はエラーメッセージを追加
        state["messages"].append(
            AIMessage(content="スクレイピングした内容がありません。")
        )
        return state

    try:
        # 記事のタイトルを抽出
        title = ""
        if (
            isinstance(scraped_data, dict)
            and "metadata" in scraped_data
            and isinstance(scraped_data["metadata"], dict)
            and "title" in scraped_data["metadata"]
        ):
            title = scraped_data["metadata"]["title"]

        # トピック抽出のプロンプト
        result = model.invoke(
            [
                SystemMessage(
                    content="あなたは記事の内容からメインのトピックを抽出するアシスタントです。"
                ),
                HumanMessage(
                    content=f"""
以下の記事の内容から、メインのトピックを抽出してください。
トピックは簡潔に、5単語以内で表現してください。

タイトル: {title}

内容:
{scraped_content}
"""
                ),
            ]
        )

        # トピックを抽出
        topic = result.content.strip() if isinstance(result.content, str) else ""

        # トピックが空の場合はタイトルをトピックとして使用
        if not topic and title:
            topic = title

        # トピックが空の場合はデフォルトのトピックを設定
        if not topic:
            topic = "最新技術トレンド"

        # deep_researchを実行して関連知識を取得
        research_result = deep_research(topic=topic)

        # 関連知識を抽出
        related_knowledge = ""
        if (
            isinstance(research_result, dict)
            and "result" in research_result
            and isinstance(research_result["result"], dict)
        ):
            report = research_result["result"].get("report", "")
            if report:
                related_knowledge = report
            else:
                # セクション情報から関連知識を構築
                sections = research_result["result"].get("sections", [])
                if sections:
                    related_knowledge = "# 関連する周辺知識\n\n"
                    for section in sections:
                        related_knowledge += f"## {section.get('title', '')}\n"
                        related_knowledge += f"{section.get('summary', '')}\n\n"

        return {
            "topic": topic,
            "related_knowledge": related_knowledge,
        }
    except Exception as e:
        # エラーが発生した場合はエラーメッセージを追加
        state["messages"].append(
            AIMessage(content=f"トピック抽出と調査中にエラーが発生しました: {str(e)}")
        )
        return state


def create_tweet(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, str]:
    """スクレイピング結果からTwitter投稿用の内容を作成する。
    インプレッションやいいねが多くなるツイートを生成する。

    Args:
        state (Dict[str, Any]): 現在の状態
        config (RunnableConfig): ランタイム設定

    Returns:
        Dict[str, str]: 投稿内容を含む辞書
    """
    url = state.get("url", "")
    scraped_data = state.get("scraped_data", {})
    scraped_content = state.get("scraped_content", "")
    topic = state.get("topic", "")
    related_knowledge = state.get("related_knowledge", "")

    if not scraped_content:
        # スクレイピングした内容がない場合はエラーメッセージを追加
        state["messages"].append(
            AIMessage(content="スクレイピングした内容がありません。")
        )
        return state

    try:
        # 記事のタイトルを抽出
        title = ""
        if (
            isinstance(scraped_data, dict)
            and "metadata" in scraped_data
            and isinstance(scraped_data["metadata"], dict)
            and "title" in scraped_data["metadata"]
        ):
            title = scraped_data["metadata"]["title"]

        article = f"""
# 記事

## タイトル
{title}

## トピック
{topic}

## URL
{url}

## 記事の内容
{scraped_content}
"""

        # 高いインプレッションとエンゲージメントを獲得した実際のツイート例
        tweet_examples = """
1. "1億円調達したときよりも 10ドル課金された時の方が 脳汁ぶっ飛ぶんだが これはガチ" [14011インプレッション, 102いいね, 261エンゲージメント]

2. "ピッチ大会で優勝することよりも 1人のユーザーが熱狂してくれてることの方が100倍嬉しいんだが" [14984インプレッション, 21いいね, 113エンゲージメント]

3. "課金アプリで売り上げ増やしたい人は superwall 使った方がいい ABテスト、デザインや価格の調整とかめっちゃ簡単にできる" [29656インプレッション, 212いいね, 390エンゲージメント]

4. "1分で生成した動画のインプレッションが8万を超えた" [2067インプレッション, 11いいね, 25エンゲージメント]

5. "@bmr_sri ほんまそれっす！！ 仮説検証が成功した感というか長らく頑張ってきた実験が成功した感じ" [105インプレッション, 1いいね, 2エンゲージメント]

6. "@bmr_sri ですよね なんというか、ほんまに最初に課金されたってウォオオオオオオ！！！って叫びたくなりますね笑" [175インプレッション, 1いいね, 7エンゲージメント]

7. "資金調達ナシ、共同創業者ナシのソロファウンダーが激増 もう完全にAIの時代きてるんよ 前時代に当たり前やと思われてた働き方は、今となっては会社を弱くするだけなんよ" [144460インプレッション, 740いいね, 2786エンゲージメント]

8. "日本人って現代では組織になると競争力がガタ落ちする特性あるらしいけど、個人単位で見たらものすごい優秀 異常に優秀 なのでソロプレナーにすごい向いてると思う" [1561インプレッション, 8いいね, 37エンゲージメント]
"""

        # 投稿構造の指示
        post_structure_instructions = """
あなたの投稿は以下の特徴を持つべきです：
1. 感情的な反応や個人的な意見を含める（「ほんまそれっす！！」「ですよね」など）
2. 驚きや発見を表現する（「ウォオオオオオオ！！！」「これはガチ」など）
3. 具体的な数字や成果を強調する（「1分で生成」「8万を超えた」など）
4. 質問形式を使って読者を巻き込む
5. カジュアルな口調を適切に使用する
6. 短く、インパクトのある文章で構成する
7. 最後にURLを含める
8. 投稿全体を280文字以内に収める
"""

        # 投稿内容のルール
        post_content_rules = """
1. 自然で会話的な口調を使用すること（堅苦しい表現は避ける）
2. 感情を表現する言葉や絵文字を適切に使うこと（「！！」「笑」など）
3. 読者に共感を呼び起こす表現を使うこと
4. 驚きや発見を強調すること
5. 具体的な数字や事実を含めること
6. 必要に応じて質問形式を使って読者の興味を引くこと
7. 最後にURLを含めること
8. 投稿を280文字以内に収めること
"""

        # 投稿作成のプロンプト
        prompt = f"""あなたはTwitterで高いインプレッションとエンゲージメントを獲得する投稿を作成する、トップクラスのマーケティング担当者です。
あなたはTwitterの投稿に変換する必要があるコンテンツに関する記事と、その記事に関連する周辺知識や業界トレンドの情報を提供されています。

あなたの同僚はすでにこのコンテンツに関する詳細な記事を作成してくれているので、時間をかけて注意深く読んでください。
記事内容を主軸としつつ、提供された周辺知識も取り入れて、読者に新たな気づきや深い洞察を与える投稿を作成してください。

以下は、実際に高いインプレッションとエンゲージメントを獲得したTwitterの投稿例です。これらをスタイルの参考にしてください：
<examples>
{tweet_examples}
</examples>

これらの例を見たところで、あなたが従うべきTwitter投稿の特徴について説明しましょう。
{post_structure_instructions}

これらの特徴を必ず取り入れてください。そして、投稿は感情的で共感を呼び起こすものであればあるほど良いことを忘れないでください。
Twitter投稿を作成する際に厳守すべきルールとガイドラインは以下の通りです：
<rules>
{post_content_rules}
</rules>

最後に、Twitter投稿を書く際には以下のプロセスに従ってください：
<writing-process>
ステップ1. まず、記事と周辺知識の情報を非常に注意深く読みます。
ステップ2. メモを取り、記事内容と周辺知識を組み合わせた考えを書き留めます。これが最初に書くテキストになります。メモと考えを「<thinking>」タグで囲みます。
ステップ3. 最後に、記事内容をメインとしつつ周辺知識からの洞察も取り入れたTwitter投稿を書きます。これが最後に書くテキストになります。投稿を「<post>」タグで囲みます。
</writing-process>

これらの例、ルール、およびユーザーから提供された記事内容と周辺知識を考慮して、高いエンゲージメントを獲得できる魅力的なTwitter投稿を作成してください。

こちらが記事です：
{article}

こちらが関連する周辺知識・業界トレンドです：
{related_knowledge}
"""

        # LLMを使用して投稿内容を生成
        result = model.invoke(
            [
                SystemMessage(
                    content="""
あなたは高いインプレッションとエンゲージメントを獲得するTwitter投稿を作成する専門家です。与えられたレポートを元に、感情的で共感を呼び起こす魅力的なツイートを作成してください。

以下の点を含めてください：
1. 感情的な表現（「ほんまそれっす！！」「ウォオオオオオオ！！！」）、カジュアルな言葉（「これはガチ」「マジやばい」など）を適切に取り入れ、親近感と共感を生み出す
2. 読者の興味を引く質問や具体的な数字
3. レポートから得られる直接的な示唆だけでなく、関連する周辺知識や業界トレンドを含めた考察
4. なぜこの情報が重要なのか、読者のビジネスや生活にどう影響するかの洞察

ユーザーが思わず共感して「いいね」したくなるような投稿を心がけてください。また、ツイートは280文字以内で作成してください。
"""
                ),
                HumanMessage(content=prompt),
            ]
        )

        # LLMの出力から投稿内容を抽出
        if isinstance(result.content, str):
            # <post>タグ内のテキストを抽出
            post_match = re.search(r"<post>(.*?)</post>", result.content, re.DOTALL)

            if post_match:
                tweet_content = post_match.group(1).strip()
            else:
                # タグが見つからない場合は、全体を使用
                tweet_content = result.content.strip()

            # 280文字を超える場合は切り詰める
            if len(tweet_content) > 280:
                tweet_content = tweet_content[:277] + "..."

            return {
                "tweet_content": tweet_content,
            }
        else:
            # 投稿内容の生成に失敗した場合はエラーメッセージを追加
            state["messages"].append(
                AIMessage(content="投稿内容の生成に失敗しました。")
            )
            return state
    except Exception as e:
        # エラーが発生した場合はエラーメッセージを追加
        state["messages"].append(
            AIMessage(content=f"投稿内容の作成中にエラーが発生しました: {str(e)}")
        )
        return state


def post_tweet(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, str]:
    """作成した内容をTwitterに投稿する。

    Args:
        state (Dict[str, Any]): 現在の状態
        config (RunnableConfig): ランタイム設定

    Returns:
        Dict[str, str]: 投稿結果を含む辞書
    """
    tweet_content = state.get("tweet_content", "")
    user_id = state.get("user_id")

    if not tweet_content:
        # 投稿内容がない場合はエラーメッセージを追加
        state["messages"].append(AIMessage(content="投稿内容がありません。"))
        return state

    try:
        # arcadepyライブラリをインポート
        from arcadepy import Arcade

        # APIキーとユーザーIDを取得
        api_key = os.getenv("ARCADE_API_KEY")
        if not api_key:
            state["messages"].append(
                AIMessage(content="ARCADE_API_KEYが設定されていません。")
            )
            # テスト用にシミュレートされたツイート結果を返す
            return {
                "tweet_result": f"Simulated tweet: {tweet_content[:50]}...",
            }

        # ユーザーIDを設定
        if not user_id:
            user_id = os.getenv("ARCADE_USER_ID")
            if not user_id:
                state["messages"].append(
                    AIMessage(
                        content="ユーザーIDが必要です。ARCADE_USER_IDを設定するか、パラメータとして渡してください。"
                    )
                )
                # テスト用にシミュレートされたツイート結果を返す
                return {
                    "tweet_result": f"Simulated tweet: {tweet_content[:50]}...",
                }

        # Arcadeクライアントを初期化
        client = Arcade(api_key=api_key)

        # ツール名を設定
        tool_name = "X.PostTweet@0.1.12"

        try:
            # ツールを認証
            auth_response = client.tools.authorize(
                tool_name=tool_name,
                user_id=user_id,
            )

            # 認証が完了しているか確認
            if auth_response.status != "completed":
                auth_url = auth_response.url
                state["messages"].append(
                    AIMessage(
                        content=f"認証が必要です。以下のURLをクリックして認証を完了してください: {auth_url}"
                    )
                )
                # テスト用にシミュレートされたツイート結果を返す
                return {
                    "tweet_result": "認証が必要です。認証後に再度お試しください。",
                }

            # 認証の完了を待機
            auth_response = client.auth.wait_for_completion(auth_response)

            if auth_response.status != "completed":
                state["messages"].append(AIMessage(content="認証に失敗しました。"))
                # テスト用にシミュレートされたツイート結果を返す
                return {
                    "tweet_result": "認証に失敗しました。再度お試しください。",
                }

            # ツールを実行
            result = client.tools.execute(
                tool_name=tool_name,
                input={"tweet_text": tweet_content},
                user_id=user_id,
            )

            return {
                "tweet_result": str(result),
            }
        except Exception as e:
            # 認証または実行に失敗した場合はエラーメッセージを追加
            state["messages"].append(
                AIMessage(
                    content=f"Twitter認証または実行中にエラーが発生しました: {str(e)}"
                )
            )
            # テスト用にシミュレートされたツイート結果を返す
            return {
                "tweet_result": f"エラーが発生しましたが、テスト用にシミュレートされたツイートを返します: {tweet_content[:50]}...",
            }
    except Exception as e:
        # エラーが発生した場合はエラーメッセージを追加
        state["messages"].append(
            AIMessage(content=f"Twitter投稿中にエラーが発生しました: {str(e)}")
        )
        return state


def add_result_message(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    """処理結果を会話に追加する。

    Args:
        state (Dict[str, Any]): 現在の状態
        config (RunnableConfig): ランタイム設定

    Returns:
        Dict[str, Any]: 更新された状態
    """
    url = state.get("url", "")
    tweet_content = state.get("tweet_content", "")
    tweet_result = state.get("tweet_result", "")

    if tweet_content and tweet_result:
        state["messages"].append(
            AIMessage(
                content=f"""
URLの内容をスクレイピングし、Twitterに投稿しました。

URL: {url}

投稿内容:
{tweet_content}

投稿結果:
{tweet_result}
"""
            )
        )

    return state


def route_after_extract_url(state: Dict[str, Any]) -> Literal["scrape_url", "end"]:
    """URLの抽出後の遷移先を決定する。

    Args:
        state (Dict[str, Any]): 現在の状態

    Returns:
        Literal["scrape_url", "end"]: 次のステップ
    """
    if state.get("url", ""):
        return "scrape_url"
    else:
        return "end"


def route_after_scrape_url(
    state: Dict[str, Any],
) -> Literal["extract_topic_and_research", "end"]:
    """URLのスクレイピング後の遷移先を決定する。

    Args:
        state (Dict[str, Any]): 現在の状態

    Returns:
        Literal["extract_topic_and_research", "end"]: 次のステップ
    """
    if state.get("error", ""):
        return "end"
    elif state.get("scraped_content", ""):
        return "extract_topic_and_research"
    else:
        return "end"


def route_after_extract_topic_and_research(
    state: Dict[str, Any],
) -> Literal["create_tweet", "end"]:
    """トピック抽出と調査後の遷移先を決定する。

    Args:
        state (Dict[str, Any]): 現在の状態

    Returns:
        Literal["create_tweet", "end"]: 次のステップ
    """
    if state.get("error", ""):
        return "end"
    elif state.get("topic", "") and state.get("related_knowledge", ""):
        return "create_tweet"
    else:
        return "end"


def route_after_create_tweet(state: Dict[str, Any]) -> Literal["post_tweet", "end"]:
    """投稿内容作成後の遷移先を決定する。

    Args:
        state (Dict[str, Any]): 現在の状態

    Returns:
        Literal["post_tweet", "end"]: 次のステップ
    """
    if state.get("error", ""):
        return "end"
    elif state.get("tweet_content", ""):
        return "post_tweet"
    else:
        return "end"


def route_after_post_tweet(
    state: Dict[str, Any],
) -> Literal["add_result_message", "end"]:
    """Twitter投稿後の遷移先を決定する。

    Args:
        state (Dict[str, Any]): 現在の状態

    Returns:
        Literal["add_result_message", "end"]: 次のステップ
    """
    if state.get("error", ""):
        return "end"
    elif state.get("tweet_result", ""):
        return "add_result_message"
    else:
        return "end"


# グラフを作成
builder = StateGraph(URLToTwitterState)

# ノードを追加
builder.add_node("extract_url", extract_url)
builder.add_node("scrape_url", scrape_url)
builder.add_node("extract_topic_and_research", extract_topic_and_research)
builder.add_node("create_tweet", create_tweet)
builder.add_node("post_tweet", post_tweet)
builder.add_node("add_result_message", add_result_message)

# エッジを追加
builder.add_edge(START, "extract_url")
builder.add_conditional_edges(
    "extract_url",
    route_after_extract_url,
    {
        "scrape_url": "scrape_url",
        "end": END,
    },
)
builder.add_conditional_edges(
    "scrape_url",
    route_after_scrape_url,
    {
        "extract_topic_and_research": "extract_topic_and_research",
        "end": END,
    },
)
builder.add_conditional_edges(
    "extract_topic_and_research",
    route_after_extract_topic_and_research,
    {
        "create_tweet": "create_tweet",
        "end": END,
    },
)
builder.add_conditional_edges(
    "create_tweet",
    route_after_create_tweet,
    {
        "post_tweet": "post_tweet",
        "end": END,
    },
)
builder.add_conditional_edges(
    "post_tweet",
    route_after_post_tweet,
    {
        "add_result_message": "add_result_message",
        "end": END,
    },
)
builder.add_edge("add_result_message", END)

# グラフをコンパイル
graph = builder.compile()


def run_url_to_twitter_agent(url: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """URLからTwitterへの投稿を行うエージェントを実行する。

    Args:
        url (str): スクレイピングするURL
        user_id (Optional[str], optional): Twitter認証用のユーザーID。デフォルトはNone。

    Returns:
        Dict[str, Any]: 処理結果
    """
    # 初期状態を設定
    initial_state: Dict[str, Any] = {
        "messages": [
            HumanMessage(content=f"このURLの内容をTwitterに投稿してください: {url}")
        ],
        "url": url,
        "user_id": user_id,
        "scraped_content": "",
        "scraped_data": {},
        "topic": "",
        "related_knowledge": "",
        "tweet_content": "",
        "tweet_result": "",
        "error": "",
    }

    # グラフを実行
    result = graph.invoke(initial_state)

    return {
        "messages": result["messages"],
        "url": result.get("url", ""),
        "scraped_content": result.get("scraped_content", ""),
        "topic": result.get("topic", ""),
        "related_knowledge": result.get("related_knowledge", ""),
        "tweet_content": result.get("tweet_content", ""),
        "tweet_result": result.get("tweet_result", ""),
        "error": result.get("error", ""),
    }
