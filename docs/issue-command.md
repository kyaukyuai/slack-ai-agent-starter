# /issue コマンド利用ガイド

## 概要

`/issue` コマンドは、Slackスレッドの会話内容を読み取り、自動的にGitHub issueを作成する機能です。Claude Code SDKを使用して会話内容を解析し、適切なタイトルと本文を生成します。

## 前提条件

### 1. 必要な環境変数

以下の環境変数を設定する必要があります：

```bash
# GitHub Personal Access Token (repo権限が必要)
GITHUB_TOKEN=your-github-personal-access-token

# デフォルトのリポジトリ（owner/repo形式）
GITHUB_REPOSITORY=owner/repo

# Claude AI API Key (issueの内容生成に使用)
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 2. GitHubトークンの作成

1. GitHubにログイン
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. "Generate new token" をクリック
4. 以下の権限を選択：
   - `repo` (Full control of private repositories)
5. トークンを生成し、安全に保管

### 3. Slackアプリの設定

#### スラッシュコマンドの追加

1. [Slack API](https://api.slack.com/apps) でアプリを開く
2. 左メニューから「Slash Commands」を選択
3. 「Create New Command」をクリック
4. 以下の情報を入力：
   - Command: `/issue`
   - Request URL: `https://your-domain.com/slack/commands`
   - Short Description: `スレッドからGitHub issueを作成`
   - Usage Hint: `[スレッドリンク]`

#### 必要なBot Token Scopes

アプリに以下のスコープが設定されていることを確認してください：

- `commands` - スラッシュコマンドの使用
- `channels:history` - パブリックチャンネルのメッセージ履歴読み取り
- `groups:history` - プライベートチャンネルのメッセージ履歴読み取り
- `im:history` - ダイレクトメッセージの履歴読み取り
- `mpim:history` - グループDMの履歴読み取り
- `chat:write` - メッセージの投稿

## 使用方法

### 1. スレッド内での実行

スレッド内で直接コマンドを実行：

```
/issue
```

現在のスレッドの会話内容からissueが作成されます。

### 2. スレッドリンクを指定

別のスレッドのリンクを指定して実行：

```
/issue https://your-workspace.slack.com/archives/C1234567/p1234567890123456
```

### 3. タイムスタンプを指定

スレッドのタイムスタンプを直接指定：

```
/issue 1234567890.123456
```

## 動作の流れ

1. **コマンド実行**: ユーザーが `/issue` コマンドを実行
2. **スレッド特定**: コマンドのパラメータまたは実行場所からスレッドを特定
3. **会話読み取り**: スレッド内のすべてのメッセージを取得
4. **内容生成**: Claude Code SDKを使用して以下を生成：
   - 簡潔で分かりやすいタイトル
   - 詳細な説明（概要、背景、期待される結果）
   - 適切なラベル
5. **issue作成**: GitHub APIを使用してissueを作成
6. **結果通知**: 作成されたissueのURLをSlackに通知

## エラーの対処

### 「GitHub tokenが設定されていません」

環境変数 `GITHUB_TOKEN` が設定されていません。`.env` ファイルに追加してください。

### 「GitHub repositoryが設定されていません」

環境変数 `GITHUB_REPOSITORY` が設定されていません。形式: `owner/repo`

### 「スレッドが見つかりません」

- スレッド内でコマンドを実行するか
- 正しいスレッドリンクを指定してください

### 「APIエラー」

- GitHubトークンの権限を確認
- リポジトリへのアクセス権限を確認
- APIレート制限を確認

## セキュリティに関する注意

- GitHubトークンは環境変数として安全に管理してください
- トークンをコードにハードコードしないでください
- 必要最小限の権限のみを付与してください
- プライベートリポジトリの場合、適切なアクセス権限を確認してください

## カスタマイズ

### issueテンプレートの変更

`slash_command_handlers.py` の `prompt` 変数を編集することで、生成されるissueの形式をカスタマイズできます。

### デフォルトラベルの設定

必要に応じて、特定のラベルを自動的に付与するようにコードを修正できます。

## トラブルシューティング

### ログの確認

エラーが発生した場合は、以下のログを確認してください：

```bash
# アプリケーションログ
tail -f slack_bot.log

# Dockerログ（Docker使用時）
docker-compose logs -f web
```

### 依存関係の確認

```bash
# 必要なパッケージがインストールされているか確認
poetry show claude-code-sdk
poetry show requests
```

### 環境変数の確認

```bash
# 設定されている環境変数を確認
env | grep GITHUB
env | grep ANTHROPIC
```

## 関連ドキュメント

- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Slack Slash Commands](https://api.slack.com/interactivity/slash-commands)
- [Claude Code SDK Documentation](https://docs.anthropic.com/ja/docs/claude-code/sdk)
