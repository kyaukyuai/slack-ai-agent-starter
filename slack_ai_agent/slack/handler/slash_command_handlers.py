"""Slash command handlers for Slack bot."""

import logging
import os
import re
from typing import Any
from typing import Dict
from typing import Optional

from slack_bolt import Ack
from slack_bolt import App
from slack_bolt import Say

from slack_ai_agent.agents.tools.github_tools import create_github_issue
from slack_ai_agent.slack.handler.conversation import get_thread_history
from slack_ai_agent.slack.handler.utils import build_conversation_history


logger = logging.getLogger(__name__)


def extract_thread_ts_from_text(text: str) -> Optional[str]:
    """スレッドのタイムスタンプをテキストから抽出する。

    Args:
        text: コマンドテキスト

    Returns:
        スレッドのタイムスタンプまたはNone
    """
    # Slackのメッセージリンクパターン: https://xxx.slack.com/archives/CHANNEL/pTIMESTAMP
    link_pattern = r"https://[^/]+\.slack\.com/archives/[^/]+/p(\d+)"
    match = re.search(link_pattern, text)
    if match:
        # pTIMESTAMP形式をタイムスタンプ形式に変換
        timestamp = match.group(1)
        # 例: p1234567890123456 -> 1234567890.123456
        return f"{timestamp[:10]}.{timestamp[10:]}"

    # 直接タイムスタンプが指定された場合
    ts_pattern = r"(\d{10}\.\d{6})"
    match = re.search(ts_pattern, text)
    if match:
        return match.group(1)

    return None


def register_slash_command_handlers(app: App) -> None:
    """スラッシュコマンドハンドラーを登録する。

    Args:
        app: Slack Boltアプリケーションインスタンス
    """

    @app.command("/issue")
    def handle_issue_command(
        ack: Ack, command: Dict[str, Any], say: Say, client: Any
    ) -> None:
        """GitHub issueを作成するスラッシュコマンドハンドラー。

        使用方法:
        1. スレッド内で実行: /issue
        2. スレッドリンクを指定: /issue https://xxx.slack.com/archives/CHANNEL/pTIMESTAMP
        3. タイムスタンプを指定: /issue 1234567890.123456

        Args:
            ack: Slackへの確認応答関数
            command: コマンド情報
            say: メッセージ送信関数
            client: Slack WebClient
        """
        # 3秒以内に確認応答を送信
        ack()

        channel_id = command["channel_id"]
        text = command.get("text", "").strip()

        # GitHub tokenの確認
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            say(
                text="❌ GitHub tokenが設定されていません。環境変数 `GITHUB_TOKEN` を設定してください。",
                thread_ts=command.get("thread_ts"),
            )
            return

        # スレッドタイムスタンプの取得
        thread_ts = None

        # 1. コマンドテキストからスレッドタイムスタンプを抽出
        if text:
            thread_ts = extract_thread_ts_from_text(text)

        # 2. スレッド内で実行された場合
        if not thread_ts and "thread_ts" in command:
            thread_ts = command["thread_ts"]

        # 3. 最新のメッセージを探す（スレッド外で実行された場合）
        if not thread_ts:
            try:
                # チャンネルの最新メッセージを取得
                result = client.conversations_history(channel=channel_id, limit=10)
                messages = result.get("messages", [])

                # スレッドを持つメッセージを探す
                for msg in messages:
                    if "thread_ts" in msg and msg.get("reply_count", 0) > 0:
                        thread_ts = msg["thread_ts"]
                        break

                if not thread_ts:
                    say(
                        text="❌ スレッドが見つかりません。スレッド内で `/issue` を実行するか、スレッドのリンクを指定してください。\n"
                        "例: `/issue https://xxx.slack.com/archives/CHANNEL/pTIMESTAMP`"
                    )
                    return

            except Exception as e:
                logger.error(f"Error getting channel history: {e}")
                say(text=f"❌ エラーが発生しました: {str(e)}")
                return

        # スレッドメッセージを取得
        say(text="🔍 スレッドの内容を読み取っています...", thread_ts=thread_ts)

        thread_messages = get_thread_history(app, channel_id, thread_ts)
        if not thread_messages:
            say(text="❌ スレッドメッセージの取得に失敗しました。", thread_ts=thread_ts)
            return

        # 会話履歴を構築
        conversation_history = build_conversation_history(thread_messages)
        if not conversation_history:
            say(
                text="❌ スレッドに有効なメッセージが見つかりません。",
                thread_ts=thread_ts,
            )
            return

        # Claude Code SDKを使用してissue内容を生成
        say(text="🤖 GitHub issueの内容を生成しています...", thread_ts=thread_ts)

        try:
            # 会話履歴からissue内容を生成
            import asyncio

            from claude_code_sdk import ClaudeCodeOptions
            from claude_code_sdk import query

            # 会話履歴を文字列に変換
            conversation_text = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in conversation_history]
            )

            prompt = f"""以下のSlackスレッドの会話内容から、GitHub issueを作成してください。

会話内容:
{conversation_text}

以下の形式でJSONを出力してください（説明は不要、JSONのみ）:
{{
  "title": "簡潔で分かりやすいタイトル",
  "body": "## 概要\\n\\n問題や要望の詳細な説明\\n\\n## 背景\\n\\n会話から読み取れる背景情報\\n\\n## 期待される結果\\n\\n解決策や実装内容\\n\\n## その他\\n\\n関連情報やメモ",
  "labels": ["適切なラベル1", "適切なラベル2"]
}}"""

            async def generate_issue_content():
                messages = []
                async for message in query(
                    prompt=prompt,
                    options=ClaudeCodeOptions(max_turns=1, output_format="stream-json"),
                ):
                    if hasattr(message, "content"):
                        messages.append(message.content)
                return "".join(messages)

            # 非同期関数を実行
            issue_content_str = asyncio.run(generate_issue_content())

            # JSON形式で解析
            import json

            issue_content = json.loads(issue_content_str)

            # GitHub issueを作成
            say(text="📝 GitHub issueを作成しています...", thread_ts=thread_ts)

            # リポジトリ情報を環境変数から取得
            github_repo = os.getenv("GITHUB_REPOSITORY", "")
            if not github_repo:
                say(
                    text="❌ GitHub repositoryが設定されていません。環境変数 `GITHUB_REPOSITORY` を設定してください。\n"
                    "例: `owner/repo`",
                    thread_ts=thread_ts,
                )
                return

            # GitHub issue作成
            issue_url = create_github_issue(
                repo=github_repo,
                title=issue_content["title"],
                body=issue_content["body"],
                labels=issue_content.get("labels", []),
            )

            # 成功メッセージ
            say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "✅ GitHub issueを作成しました！",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*タイトル:* {issue_content['title']}\n*URL:* <{issue_url}|{issue_url}>",
                        },
                    },
                ],
                text=f"✅ GitHub issueを作成しました: {issue_url}",
                thread_ts=thread_ts,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            say(
                text="❌ issueの内容生成中にエラーが発生しました。JSONの解析に失敗しました。",
                thread_ts=thread_ts,
            )
        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}")
            say(
                text=f"❌ GitHub issueの作成中にエラーが発生しました: {str(e)}",
                thread_ts=thread_ts,
            )
