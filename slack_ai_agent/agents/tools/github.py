import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from langchain.tools import StructuredTool
from langchain.tools import Tool
from langchain_arcade import ArcadeToolManager


def create_github_tools() -> Optional[List[Union[Tool, StructuredTool]]]:
    """Create and return GitHub tools using Arcade.

    This module requires proper GitHub authentication setup through the Arcade Dashboard:
    1. Create a GitHub app in GitHub Developer Settings
       - Enable necessary permissions (at minimum, Account > Email addresses)
       - Set redirect URL to: https://cloud.arcade.dev/api/v1/oauth/callback
       - Copy the client ID and secret
    2. Configure in Arcade Dashboard:
       - Go to OAuth section and click "Add OAuth Provider"
       - Select GitHub provider
       - Enter your GitHub app's client ID and secret
       - Save the configuration

    Returns:
        Optional[List[Union[Tool, StructuredTool]]]: List of GitHub tools if ARCADE_API_KEY is available, None otherwise.
    """
    try:
        # Initialize the tool manager
        tool_manager = ArcadeToolManager()

        # Get GitHub tools
        tools = tool_manager.get_tools(toolkits=["Github"])

        def check_auth(tool_name: str, user_id: str) -> None:
            """Check and handle tool authorization if needed.

            Args:
                tool_name: The name of the tool to check.
                user_id: The user ID to authenticate.
            """
            if tool_manager.requires_auth(tool_name):
                auth_response = tool_manager.authorize(tool_name, user_id)
                if auth_response.status != "completed":
                    print(f"Visit the following URL to authorize: {auth_response.url}")
                    if auth_response.id:  # Check if id exists
                        tool_manager.wait_for_auth(auth_response.id)
                        if not tool_manager.is_authorized(auth_response.id):
                            raise ValueError("Authorization failed")

        def set_starred(args: Dict[str, Any]) -> str:
            """Star or unstar a GitHub repository.

            First-time users will be prompted to authorize through GitHub OAuth.

            Args:
                args: Dictionary containing:
                    - owner: Repository owner
                    - name: Repository name
                    - starred: Boolean indicating whether to star (True) or unstar (False)
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Github.SetStarred"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={
                        "owner": args["owner"],
                        "name": args["name"],
                        "starred": args["starred"],
                    },
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error setting star status: {str(e)}"

        def create_issue(args: Dict[str, Any]) -> str:
            """Create an issue in a GitHub repository.

            First-time users will be prompted to authorize through GitHub OAuth.

            Args:
                args: Dictionary containing:
                    - owner: Repository owner
                    - name: Repository name
                    - title: Issue title
                    - body: Issue body/content
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Github.CreateIssue"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={
                        "owner": args["owner"],
                        "name": args["name"],
                        "title": args["title"],
                        "body": args["body"],
                    },
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error creating issue: {str(e)}"

        def create_issue_comment(args: Dict[str, Any]) -> str:
            """Create a comment on an issue in a GitHub repository.

            First-time users will be prompted to authorize through GitHub OAuth.

            Args:
                args: Dictionary containing:
                    - owner: Repository owner
                    - name: Repository name
                    - issue_number: The number that identifies the issue
                    - body: The contents of the comment
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Github.CreateIssueComment"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={
                        "owner": args["owner"],
                        "repo": args["name"],
                        "issue_number": args["issue_number"],
                        "body": args["body"],
                    },
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error creating issue comment: {str(e)}"

        def create_review_reply(args: Dict[str, Any]) -> str:
            """Create a reply to a review comment on a pull request.

            First-time users will be prompted to authorize through GitHub OAuth.

            Args:
                args: Dictionary containing:
                    - owner: Repository owner
                    - name: Repository name
                    - pull_number: The number that identifies the pull request
                    - comment_id: The unique identifier of the comment to reply to
                    - body: The text of the reply comment
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Github.CreateReplyForReviewComment"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={
                        "owner": args["owner"],
                        "repo": args["name"],
                        "pull_number": args["pull_number"],
                        "comment_id": args["comment_id"],
                        "body": args["body"],
                    },
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error creating review reply: {str(e)}"

        def list_pull_requests(args: Dict[str, Any]) -> str:
            """List pull requests in a GitHub repository.

            First-time users will be prompted to authorize through GitHub OAuth.

            Args:
                args: Dictionary containing:
                    - owner: Repository owner
                    - name: Repository name
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Github.ListPullRequests"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={"owner": args["owner"], "name": args["name"]},
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error listing pull requests: {str(e)}"

        def get_repository_info(args: Dict[str, Any]) -> str:
            """Get repository information using Arcade GitHub tool.

            First-time users will be prompted to authorize through GitHub OAuth.

            Args:
                args: Dictionary containing:
                    - owner: Repository owner
                    - name: Repository name
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Repository information.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Github.GetRepository"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={"owner": args["owner"], "name": args["name"]},
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error fetching repository information: {str(e)}"

        # Create custom tool wrappers
        custom_tools = [
            Tool.from_function(
                func=set_starred,
                name="github_set_starred",
                description="Star or unstar a GitHub repository (public or private). First-time users will be prompted to authorize. Input should be a dictionary with 'owner', 'name', 'starred' (boolean), and optional 'user_id' keys.",
            ),
            Tool.from_function(
                func=create_issue,
                name="github_create_issue",
                description="Create an issue in a GitHub repository (public or private). First-time users will be prompted to authorize. Input should be a dictionary with 'owner', 'name', 'title', 'body', and optional 'user_id' keys.",
            ),
            Tool.from_function(
                func=create_issue_comment,
                name="github_create_issue_comment",
                description="Create a comment on an issue in a GitHub repository (public or private). First-time users will be prompted to authorize. Input should be a dictionary with 'owner', 'name', 'issue_number', 'body', and optional 'user_id' keys.",
            ),
            Tool.from_function(
                func=create_review_reply,
                name="github_create_review_reply",
                description="Create a reply to a review comment on a pull request (public or private). First-time users will be prompted to authorize. Input should be a dictionary with 'owner', 'name', 'pull_number', 'comment_id', 'body', and optional 'user_id' keys.",
            ),
            Tool.from_function(
                func=list_pull_requests,
                name="github_list_pull_requests",
                description="List pull requests in a GitHub repository (public or private). First-time users will be prompted to authorize. Input should be a dictionary with 'owner', 'name', and optional 'user_id' keys.",
            ),
            Tool.from_function(
                func=get_repository_info,
                name="github_get_repository_info",
                description="Get detailed information about a GitHub repository (public or private). First-time users will be prompted to authorize. Input should be a dictionary with 'owner', 'name', and optional 'user_id' keys.",
            ),
        ]

        # Combine Arcade's GitHub tools with our custom wrappers
        return tools + custom_tools

    except Exception as e:
        print(f"Failed to create GitHub tools: {e}")
        return None
