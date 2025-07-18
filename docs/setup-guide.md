# セットアップガイド

このガイドでは、Slack AI Agent Starterの初期設定手順を説明します。

## 目次

1. [前提条件](#前提条件)
2. [環境構築](#環境構築)
3. [Slackアプリの作成と設定](#slackアプリの作成と設定)
4. [環境変数の設定](#環境変数の設定)
5. [アプリケーションの起動](#アプリケーションの起動)
6. [動作確認](#動作確認)

## 前提条件

- Python 3.11以上
- Node.js (Claude Code SDK用)
- Poetry (Pythonパッケージ管理)
- Docker & Docker Compose (オプション)
- Slackワークスペースの管理者権限

## 環境構築

### 1. リポジトリのクローン

```bash
git clone https://github.com/kyaukyuai/slack-ai-agent-starter.git
cd slack-ai-agent-starter
```

### 2. Poetryを使用した依存関係のインストール

```bash
# Poetryがインストールされていない場合
curl -sSL https://install.python-poetry.org | python3 -

# 依存関係のインストール
poetry install
```

### 3. Claude Code CLIのインストール

```bash
npm install -g @anthropic-ai/claude-code
```

## Slackアプリの作成と設定

### 1. Slackアプリの作成

1. [Slack API](https://api.slack.com/apps)にアクセス
2. "Create New App"をクリック
3. "From scratch"を選択
4. アプリ名とワークスペースを選択

### 2. Bot Token Scopesの設定

OAuth & Permissions ページで以下のスコープを追加：

**Bot Token Scopes:**
- `app_mentions:read` - メンションの読み取り
- `channels:history` - パブリックチャンネルの履歴
- `channels:read` - パブリックチャンネル情報の読み取り
- `chat:write` - メッセージの送信
- `commands` - スラッシュコマンド
- `groups:history` - プライベートチャンネルの履歴
- `groups:read` - プライベートチャンネル情報の読み取り
- `im:history` - DMの履歴
- `im:read` - DM情報の読み取り
- `mpim:history` - グループDMの履歴
- `mpim:read` - グループDM情報の読み取り

### 3. Event Subscriptionsの設定

1. Event Subscriptionsページで "Enable Events"をON
2. Request URLに `https://your-domain.com/slack/events` を設定
3. Subscribe to bot eventsで以下を追加：
   - `app_mention` - アプリへのメンション
   - `message.channels` - チャンネルメッセージ
   - `message.groups` - プライベートチャンネルメッセージ
   - `message.im` - DMメッセージ
   - `message.mpim` - グループDMメッセージ

### 4. Slash Commandsの設定

Slash Commandsページで新しいコマンドを追加：

#### /issueコマンド
- Command: `/issue`
- Request URL: `https://your-domain.com/slack/commands`
- Short Description: `スレッドからGitHub issueを作成`
- Usage Hint: `[スレッドリンク]`

### 5. アプリのインストール

1. Install Appページでワークスペースにインストール
2. Bot User OAuth Tokenをコピー（後で使用）

## 環境変数の設定

### 1. .envファイルの作成

```bash
cp .env.example .env
```

### 2. 必要な環境変数の設定

`.env`ファイルを編集：

```bash
# Slack設定（必須）
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_BOT_TOKEN=xoxb-your-bot-token

# AI設定（いずれか必須）
ANTHROPIC_API_KEY=your-anthropic-api-key  # Claude使用時
OPENAI_API_KEY=your-openai-api-key       # GPT使用時（埋め込みにも使用）

# GitHub設定（/issueコマンド使用時必須）
GITHUB_TOKEN=your-github-personal-access-token
GITHUB_REPOSITORY=owner/repo

# 検索機能（オプション）
TAVILY_API_KEY=your-tavily-api-key
PERPLEXITY_API_KEY=your-perplexity-api-key

# Web scraping（オプション）
FIRECRAWL_API_KEY=your-firecrawl-api-key

# LangGraph設定
LANGGRAPH_URL=http://localhost:2024
LANGGRAPH_TOKEN=admin

# 開発設定
ENVIRONMENT=development
PORT=3000
```

### 3. 各種APIキーの取得方法

#### Anthropic API Key
1. [Anthropic Console](https://console.anthropic.com/)にアクセス
2. API Keysセクションで新しいキーを生成

#### GitHub Personal Access Token
1. GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. `repo`権限を選択

#### Tavily API Key
1. [Tavily](https://tavily.com/)でアカウント作成
2. ダッシュボードからAPIキーを取得

## アプリケーションの起動

### Dockerを使用する場合

```bash
# すべてのサービスを起動
make dev

# または個別に起動
make dev-langgraph  # LangGraphサーバー
make dev-web       # Webサーバー
```

### ローカル環境で直接起動

```bash
# LangGraphサーバーの起動（別ターミナル）
poetry run langgraph up

# Slackアプリの起動
poetry run python -m slack_ai_agent.slack.app
```

## 動作確認

### 1. 基本的な動作確認

Slackでボットにメンションして応答を確認：

```
@your-bot-name こんにちは
```

### 2. /issueコマンドの動作確認

1. テスト用のスレッドを作成
2. スレッド内で `/issue` を実行
3. GitHub issueが作成されることを確認

### 3. ログの確認

問題が発生した場合：

```bash
# アプリケーションログ
tail -f slack_bot.log

# Dockerログ
docker-compose logs -f
```

## トラブルシューティング

### ポートが使用中の場合

```bash
# 使用中のポートを確認
lsof -i :3000
lsof -i :2024

# プロセスを終了
kill -9 <PID>

# または別のポートを使用
PORT=3001 poetry run python -m slack_ai_agent.slack.app
```

### Slack署名の検証エラー

- Signing Secretが正しいか確認
- Request URLがHTTPSであることを確認

### APIキーのエラー

- 各APIキーが正しく設定されているか確認
- 環境変数が正しく読み込まれているか確認：

```bash
poetry run python -c "import os; print(os.getenv('ANTHROPIC_API_KEY'))"
```

## 次のステップ

- [/issueコマンドの利用ガイド](./issue-command.md)
- [エージェントのカスタマイズ](../README_ja.md#エージェントの拡張)
- [新しいツールの追加](../README_ja.md#ツールの追加)
