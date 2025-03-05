"""Example of using the PowerPoint agent."""

import os
import sys


# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from slack_ai_agent.agents.powerpoint_agent import run_powerpoint_agent


def main():
    """Run the PowerPoint agent example."""
    # Example conversation with requirements for a PowerPoint presentation
    messages = [
        {
            "role": "user",
            "content": """
# パワーポイント作成要件

## タイトル
Pythonプログラミング入門

## 目的
プログラミング初心者にPythonの基本を紹介する

## 対象者
プログラミング未経験者、Python初心者

## 主要なトピック
- Pythonとは何か
- Pythonのインストール方法
- 基本的な文法（変数、条件分岐、ループ）
- 関数の定義と使用方法
- モジュールとパッケージ
- 実践的な例（簡単なプログラム作成）

## スタイルと形式
- シンプルで読みやすいデザイン
- コード例を含める
- 図や表を使って視覚的に説明

## 特別な要望
- 各トピックの最後に練習問題を入れる
- 参考資料やリソースのリストを最後に追加
            """,
        },
        {
            "role": "assistant",
            "content": """
パワーポイント作成要件を確認しました。以下の内容で進めてよろしいでしょうか？

# パワーポイント作成要件

## タイトル
Pythonプログラミング入門

## 目的
プログラミング初心者にPythonの基本を紹介する

## 対象者
プログラミング未経験者、Python初心者

## 主要なトピック
- Pythonとは何か
- Pythonのインストール方法
- 基本的な文法（変数、条件分岐、ループ）
- 関数の定義と使用方法
- モジュールとパッケージ
- 実践的な例（簡単なプログラム作成）

## スタイルと形式
- シンプルで読みやすいデザイン
- コード例を含める
- 図や表を使って視覚的に説明

## 特別な要望
- 各トピックの最後に練習問題を入れる
- 参考資料やリソースのリストを最後に追加
            """,
        },
        {"role": "user", "content": "はい、この要件で作成してください。"},
    ]

    # Run the PowerPoint agent
    result = run_powerpoint_agent(messages)

    # Print the result
    print("\nPowerPoint Generation Result:")
    print(
        f"PowerPoint file created at: {result.get('powerpoint_path', 'Unknown path')}"
    )


if __name__ == "__main__":
    main()
