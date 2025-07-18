"""GitHub tools for creating issues, pull requests, and other GitHub operations."""

import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests  # type: ignore[import-untyped]


def create_github_issue(
    repo: str,
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
) -> str:
    """GitHub APIを直接使用してissueを作成する。

    Args:
        repo: リポジトリ名（owner/repo形式）
        title: issueのタイトル
        body: issueの本文
        labels: ラベルのリスト（オプション）
        assignees: アサインするユーザーのリスト（オプション）

    Returns:
        作成されたissueのURL

    Raises:
        ValueError: GitHub tokenが設定されていない場合
        requests.RequestException: API呼び出しに失敗した場合
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError(
            "GitHub token is not set. Please set GITHUB_TOKEN environment variable."
        )

    # GitHub API URL
    api_url = f"https://api.github.com/repos/{repo}/issues"

    # リクエストヘッダー
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # リクエストボディ
    data: Dict[str, Any] = {
        "title": title,
        "body": body,
    }

    if labels:
        data["labels"] = labels

    if assignees:
        data["assignees"] = assignees

    # APIリクエスト
    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code == 201:
        issue_data = response.json()
        return issue_data["html_url"]
    else:
        raise requests.RequestException(
            f"Failed to create issue: {response.status_code} - {response.text}"
        )


def get_github_issue(repo: str, issue_number: int) -> Dict[str, Any]:
    """GitHub issueの詳細を取得する。

    Args:
        repo: リポジトリ名（owner/repo形式）
        issue_number: issue番号

    Returns:
        issueの詳細情報

    Raises:
        ValueError: GitHub tokenが設定されていない場合
        requests.RequestException: API呼び出しに失敗した場合
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError(
            "GitHub token is not set. Please set GITHUB_TOKEN environment variable."
        )

    # GitHub API URL
    api_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"

    # リクエストヘッダー
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # APIリクエスト
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise requests.RequestException(
            f"Failed to get issue: {response.status_code} - {response.text}"
        )


def list_github_issues(
    repo: str,
    state: str = "open",
    labels: Optional[List[str]] = None,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """GitHub issueのリストを取得する。

    Args:
        repo: リポジトリ名（owner/repo形式）
        state: issueの状態（open, closed, all）
        labels: フィルタリングするラベルのリスト
        limit: 取得する最大数

    Returns:
        issueのリスト

    Raises:
        ValueError: GitHub tokenが設定されていない場合
        requests.RequestException: API呼び出しに失敗した場合
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError(
            "GitHub token is not set. Please set GITHUB_TOKEN environment variable."
        )

    # GitHub API URL
    api_url = f"https://api.github.com/repos/{repo}/issues"

    # リクエストヘッダー
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # クエリパラメータ
    params: Dict[str, Any] = {
        "state": state,
        "per_page": min(limit, 100),  # GitHub APIの最大値は100
    }

    if labels:
        params["labels"] = ",".join(labels)

    # APIリクエスト
    response = requests.get(api_url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        raise requests.RequestException(
            f"Failed to list issues: {response.status_code} - {response.text}"
        )
