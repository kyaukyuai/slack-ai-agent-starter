"""Slack utilities module.

This module provides utility functions for Slack message formatting and LangGraph integration.
"""

import logging
import re
import time
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from dotenv import load_dotenv
from langgraph_sdk import get_sync_client
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_sdk.web import SlackResponse


# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

# Constants
MESSAGE_UPDATE_INTERVAL = 0.3  # seconds
BOT_MENTION_PATTERN = r"<@[A-Z0-9]+>\s*"
SLACK_MSG_CHAR_LIMIT = 1500  # Slackメッセージの文字数制限（約4000文字）


def split_message(message: str, limit: int = SLACK_MSG_CHAR_LIMIT) -> list[str]:
    """長いメッセージを文字数制限内の複数のメッセージに分割します。

    引数:
        message: 元の長いメッセージ
        limit: メッセージごとの文字数制限

    戻り値:
        list[str]: メッセージチャンクのリスト
    """
    if len(message) <= limit:
        return [message]

    # 適切な分割ポイントを見つける（できれば段落区切りで）
    chunks = []
    while message:
        if len(message) <= limit:
            chunks.append(message)
            break

        # 段落/改行で分割を試みる
        split_point = message[:limit].rfind("\n\n")
        if split_point == -1:
            # 段落区切りがない場合は通常の改行を試す
            split_point = message[:limit].rfind("\n")

        if split_point == -1 or split_point < limit // 2:
            # 適切な改行が見つからないか、テキストの早い段階にある場合は、
            # スペースでの分割にフォールバック
            split_point = message[:limit].rfind(" ")

        if split_point == -1:
            # スペースが見つからない場合は、制限でそのまま分割
            split_point = limit

        chunks.append(message[:split_point])
        message = message[split_point:].lstrip()

    return chunks


def post_message_chunks(
    say: Any,
    message: str,
    thread_ts: str,
    user: Optional[str] = None,
    limit: int = SLACK_MSG_CHAR_LIMIT,
) -> None:
    """メッセージを投稿し、必要に応じて分割します。

    引数:
        say: メッセージを送信するための関数
        message: 投稿するメッセージ
        thread_ts: スレッドのタイムスタンプ
        user: ユーザーID (オプション)
        limit: メッセージごとの文字数制限
    """
    # 進捗表示の追加に必要なスペースを確保するために、実際の制限を少し減らす
    # "(1/10) " のような表示に最大10文字程度使用する可能性を考慮
    progress_indicator_space = 10
    effective_limit = limit - progress_indicator_space

    chunks = split_message(message, effective_limit)
    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        try:
            # 進捗表示を追加
            progress_indicator = f"({i + 1}/{total_chunks}) "

            if i == 0 and user:  # 最初のチャンクにのみメンションを追加
                text = f"<@{user}>\n{progress_indicator}{chunk}"
            else:
                text = f"{progress_indicator}{chunk}"

            say(text=text, thread_ts=thread_ts)
        except Exception as e:
            logger.error(f"メッセージチャンクの投稿中にエラーが発生しました: {e}")


def format_for_slack_display(text: str) -> str:
    """Convert Markdown text for Slack display.

    Args:
        text: Text to convert

    Returns:
        str: Text converted for Slack display
    """
    # Process headings (#)
    text = re.sub(r"#+ (.+?)(?:\n|$)", r"*\1*\n", text)

    # Convert bullet points for better visibility
    text = re.sub(r"^\s*[-*]\s", "• ", text, flags=re.MULTILINE)

    # Process bold text (**text** -> *text*)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Process code blocks
    text = re.sub(r"```(\w+)\n", "```\n", text)

    # Adjust line breaks between paragraphs
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Add line breaks around bullet points for better readability
    text = re.sub(r"(?<!\n)\n•", "\n\n•", text)

    return text


def extract_text_from_blocks(blocks: List[Dict[str, Any]]) -> str:
    """Extract text from Slack message blocks.

    Args:
        blocks: Slack message blocks

    Returns:
        str: Extracted text
    """
    texts = set()
    for block in blocks:
        if block.get("type") == "rich_text":
            for element in block.get("elements", []):
                for rich_text in element.get("elements", []):
                    if text := rich_text.get("text", ""):
                        texts.add(text)
        elif "text" in block:
            if isinstance(block["text"], str):
                texts.add(block["text"])
            elif isinstance(block["text"], dict) and "text" in block["text"]:
                texts.add(block["text"]["text"])
    return " ".join(sorted(texts))


def build_conversation_history(
    thread_messages: Optional[Union[Dict[str, Any], SlackResponse]] = None,
    question: str = "",
) -> List[Dict[str, str]]:
    """Build conversation history.

    Args:
        thread_messages: Thread message history
        question: Current question

    Returns:
        List[Dict[str, str]]: Constructed conversation history
    """
    messages = []
    if thread_messages and "messages" in thread_messages:
        for msg in thread_messages["messages"]:
            if "blocks" in msg:
                message_text = extract_text_from_blocks(msg["blocks"])
            else:
                message_text = msg.get("text", "")

            cleaned_text = re.sub(BOT_MENTION_PATTERN, "", message_text).strip()
            if cleaned_text:
                timestamp = float(msg.get("ts", "0"))
                formatted_time = datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                if msg.get("bot_id"):
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"[{formatted_time}] Assistant: {cleaned_text}",
                        }
                    )
                else:
                    user_id = msg.get("user", "")
                    messages.append(
                        {
                            "role": "human",
                            "content": f"[{formatted_time}] User {user_id}: {cleaned_text}",
                        }
                    )

    if question:
        messages.append({"role": "user", "content": question})

    return messages


def update_slack_message(
    app: App,
    message: Dict[str, Any],
    user: str,
    formatted_text: str,
) -> None:
    """Update a Slack message.

    Args:
        app: Slack Bolt application instance
        message: Message to update
        user: User ID
        formatted_text: Formatted text
    """
    try:
        # ユーザーメンションと改行分の長さを計算
        mention_prefix = f"<@{user}>\n"
        mention_length = len(mention_prefix)

        # 実際の利用可能な文字数 (メンション分を差し引く)
        available_length = SLACK_MSG_CHAR_LIMIT - mention_length - 10  # 10は余裕分

        # メッセージが文字数制限を超えているか確認
        if len(formatted_text) > available_length:
            # 文字数制限内で短くする
            truncated_text = formatted_text[:available_length] + "...(続く)"
            app.client.chat_update(
                channel=message["channel"],
                ts=message["ts"],
                text=f"{mention_prefix}{truncated_text}",
            )
        else:
            app.client.chat_update(
                channel=message["channel"],
                ts=message["ts"],
                text=f"{mention_prefix}{formatted_text}",
            )
    except SlackApiError as slack_e:
        # Extract detailed information from Slack API errors
        response = slack_e.response
        # Direct access to data as a dict
        error_data = getattr(response, "data", {})
        # Use the request URL from the response
        url = getattr(response, "api_url", "unknown")
        error_message = f"Error updating message: The request to the Slack API failed. (url: {url}) Error: {error_data.get('error', 'unknown')}, Details: {error_data}"
        logger.error(error_message)
    except Exception as e:
        # Handle generic exceptions
        logger.error(f"Error updating message: {e}")


def process_langgraph_stream(
    client: Any,
    thread_id: str,
    messages: List[Dict[str, str]],
    say: Any,
    user: str,
    thread_ts: Optional[str],
    app: Optional[App],
) -> Optional[str]:
    """Process LangGraph stream.

    Args:
        client: LangGraph client
        thread_id: Thread ID
        messages: Conversation history
        say: Function for sending messages
        user: User ID
        thread_ts: Thread timestamp
        app: Slack Bolt application instance

    Returns:
        Optional[str]: Generated response
    """
    final_answer = ""
    last_update = time.time()
    last_post_text = ""
    message = None
    formatted_text = ""
    current_message_too_long = False

    try:
        stream = client.runs.stream(
            thread_id,
            assistant_id="agent",
            input={"messages": messages},
            stream_mode="events",
            config={
                "configurable": {"user_id": user},
            },
        )

        for chunk in stream:
            # チャンクが文字列の場合はスキップ
            if isinstance(chunk, str):
                continue

            # データ構造の確認とバリデーション
            if not hasattr(chunk, "data"):
                continue

            data = chunk.data
            if not isinstance(data, dict):
                continue

            if data.get("event") != "on_chat_model_stream":
                continue

            chunk_data = data.get("data", {})
            if not isinstance(chunk_data, dict):
                continue

            chunk_content = chunk_data.get("chunk", {}).get("content", [])
            if not chunk_content:
                continue

            content_item = chunk_content[0]
            if not isinstance(content_item, dict):
                continue

            text = content_item.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue

            # 文字化けや不正な文字列をフィルタリング
            text = "".join(char for char in text if ord(char) < 0x10000)

            final_answer += text
            formatted_text = format_for_slack_display(final_answer)

            # 文字数を確認
            if len(formatted_text) > SLACK_MSG_CHAR_LIMIT:
                # 文字数制限を超えそうな場合は更新を停止し、最終的に分割して投稿する
                current_message_too_long = True
                continue

            try:
                if not message:
                    message = say(
                        text=f"<@{user}>\n{formatted_text}",
                        thread_ts=thread_ts,
                    )
                elif app and (time.time() - last_update) > MESSAGE_UPDATE_INTERVAL:
                    last_update = time.time()
                    last_post_text = formatted_text
                    update_slack_message(app, message, user, formatted_text)
            except SlackApiError as slack_e:
                # Extract detailed information from Slack API errors
                response = slack_e.response
                # Direct access to data as a dict
                error_data = getattr(response, "data", {})
                # Use the request URL from the response
                url = getattr(response, "api_url", "unknown")
                error_message = f"Error updating message: The request to the Slack API failed. (url: {url}) Error: {error_data.get('error', 'unknown')}, Details: {error_data}"
                logger.error(error_message)
                continue
            except Exception as e:
                # Handle generic exceptions
                logger.error(f"Error updating message: {e}")
                continue

        # ストリーミング終了後の処理
        if current_message_too_long:
            # メッセージが長すぎる場合のみ分割して投稿する
            if message and app:
                # 既存のメッセージを短いバージョンに更新
                truncated_text = "長文のため分割して投稿します..."
                try:
                    app.client.chat_update(
                        channel=message["channel"],
                        ts=message["ts"],
                        text=f"<@{user}>\n{truncated_text}",
                    )
                except SlackApiError as slack_e:
                    # Extract detailed information from Slack API errors
                    response = slack_e.response
                    # Direct access to data as a dict
                    error_data = getattr(response, "data", {})
                    # Use the request URL from the response
                    url = getattr(response, "api_url", "unknown")
                    error_message = f"Error updating message to placeholder: The request to the Slack API failed. (url: {url}) Error: {error_data.get('error', 'unknown')}, Details: {error_data}"
                    logger.error(error_message)
                except Exception as e:
                    # Handle generic exceptions
                    logger.error(f"Error updating message to placeholder: {e}")

                # 完全な回答を複数のメッセージに分割して投稿
                if (
                    thread_ts
                ):  # Ensure thread_ts is not None before passing to post_message_chunks
                    post_message_chunks(
                        lambda text, thread_ts=thread_ts: say(
                            text=text, thread_ts=thread_ts
                        ),
                        formatted_text,
                        thread_ts,
                        user,
                    )
                else:
                    # If thread_ts is None, post without a thread reference
                    post_message_chunks(
                        lambda text: say(text=text),
                        formatted_text,
                        "",  # Empty string as a fallback for thread_ts
                        user,
                    )
        elif message and app and last_post_text != formatted_text:
            # メッセージが長すぎない場合は、最後の更新だけを行う
            update_slack_message(app, message, user, formatted_text)

        return final_answer

    except Exception as e:
        logger.error(f"Error in process_langgraph_stream: {e}")
        return None


def execute_langgraph(
    question: str,
    say: Any,
    user: str,
    thread_ts: Optional[str] = None,
    thread_messages: Optional[Union[Dict[str, Any], SlackResponse]] = None,
    app: Optional[App] = None,
    langgraph_url: Optional[str] = None,
    langgraph_token: Optional[str] = None,
) -> Optional[str]:
    """Execute LangGraph and generate a response.

    Args:
        question: Question text
        say: Function for sending messages
        user: User ID
        thread_ts: Thread timestamp
        thread_messages: Thread message history
        app: Slack Bolt application instance
        langgraph_url: LangGraph API URL
        langgraph_token: LangGraph API token

    Returns:
        Optional[str]: Generated response
    """
    if not langgraph_url or not langgraph_token:
        logger.error("LANGGRAPH_URL or LANGGRAPH_TOKEN is not set")
        return None

    try:
        client = get_sync_client(
            url=langgraph_url,
            headers={"Authorization": f"Bearer {langgraph_token}"},
        )
        thread = client.threads.create()
        logger.info(f"Created thread: {thread}")

        # スレッドIDが文字列として返される場合の対応
        thread_id = thread if isinstance(thread, str) else thread.get("thread_id")
        if not thread_id:
            logger.error("Failed to get thread_id")
            return None

        messages = build_conversation_history(thread_messages, question)
        return process_langgraph_stream(
            client, thread_id, messages, say, user, thread_ts, app
        )

    except Exception as e:
        logger.error(f"Error in execute_langgraph: {e}")
        return None
