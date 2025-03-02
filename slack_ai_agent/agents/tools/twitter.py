import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from langchain.tools import StructuredTool
from langchain.tools import Tool
from langchain_arcade import ArcadeToolManager


def create_twitter_tools() -> Optional[List[Union[Tool, StructuredTool]]]:
    """Create and return Twitter (X) tools using Arcade.

    This module requires proper Twitter authentication setup through the Arcade Dashboard:
    1. Create a Twitter developer account and app
       - Set up the necessary permissions
       - Set redirect URL to: https://cloud.arcade.dev/api/v1/oauth/callback
       - Copy the client ID and secret
    2. Configure in Arcade Dashboard:
       - Go to OAuth section and click "Add OAuth Provider"
       - Select Twitter provider
       - Enter your Twitter app's client ID and secret
       - Save the configuration

    Returns:
        Optional[List[Union[Tool, StructuredTool]]]: List of Twitter tools if ARCADE_API_KEY is available, None otherwise.
    """
    try:
        # Initialize the tool manager
        tool_manager = ArcadeToolManager()

        # Get Twitter tools
        tools = tool_manager.get_tools(toolkits=["X"])

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

        def lookup_tweet_by_id(args: Dict[str, Any]) -> str:
            """Look up a tweet by its ID.

            First-time users will be prompted to authorize through Twitter OAuth.

            Args:
                args: Dictionary containing:
                    - tweet_id: The ID of the tweet to look up
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message containing tweet information.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "X.LookupTweetById"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={"tweet_id": args["tweet_id"]},
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error looking up tweet: {str(e)}"

        def post_tweet(args: Dict[str, Any]) -> str:
            """Post a new tweet.

            First-time users will be prompted to authorize through Twitter OAuth.

            Args:
                args: Dictionary containing:
                    - text: The content of the tweet
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "X.PostTweet"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={"text": args["text"]},
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error posting tweet: {str(e)}"

        def get_user_profile(args: Dict[str, Any]) -> str:
            """Get a Twitter user's profile information.

            First-time users will be prompted to authorize through Twitter OAuth.

            Args:
                args: Dictionary containing:
                    - username: The Twitter username (without @)
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message containing user profile information.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "X.GetUserProfile"

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={"username": args["username"]},
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error getting user profile: {str(e)}"

        def search_tweets(args: Dict[str, Any]) -> str:
            """Search for tweets based on a query.

            First-time users will be prompted to authorize through Twitter OAuth.

            Args:
                args: Dictionary containing:
                    - query: The search query
                    - max_results: (Optional) Maximum number of results to return
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message containing search results.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "X.SearchTweets"
            max_results = args.get("max_results", 10)

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={
                        "query": args["query"],
                        "max_results": max_results,
                    },
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error searching tweets: {str(e)}"

        def get_user_timeline(args: Dict[str, Any]) -> str:
            """Get a user's timeline (recent tweets).

            First-time users will be prompted to authorize through Twitter OAuth.

            Args:
                args: Dictionary containing:
                    - username: The Twitter username (without @)
                    - max_results: (Optional) Maximum number of results to return
                    - user_id: (Optional) User identifier for authentication

            Returns:
                str: Response message containing timeline tweets.
            """
            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "X.GetUserTimeline"
            max_results = args.get("max_results", 10)

            try:
                check_auth(tool_name, user_id)
                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input={
                        "username": args["username"],
                        "max_results": max_results,
                    },
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error getting user timeline: {str(e)}"

        # Create custom tool wrappers
        custom_tools: List[Union[Tool, StructuredTool]] = [
            # Tool.from_function(
            #     func=lookup_tweet_by_id,
            #     name="twitter_lookup_tweet",
            #     description="Look up a tweet by its ID. First-time users will be prompted to authorize. Input should be a dictionary with 'tweet_id' and optional 'user_id' keys.",
            # ),
            # Tool.from_function(
            #     func=post_tweet,
            #     name="twitter_post_tweet",
            #     description="Post a new tweet. First-time users will be prompted to authorize. Input should be a dictionary with 'text' and optional 'user_id' keys.",
            # ),
            # Tool.from_function(
            #     func=get_user_profile,
            #     name="twitter_get_user_profile",
            #     description="Get a Twitter user's profile information. First-time users will be prompted to authorize. Input should be a dictionary with 'username' and optional 'user_id' keys.",
            # ),
            # Tool.from_function(
            #     func=search_tweets,
            #     name="twitter_search_tweets",
            #     description="Search for tweets based on a query. First-time users will be prompted to authorize. Input should be a dictionary with 'query', optional 'max_results', and optional 'user_id' keys.",
            # ),
            # Tool.from_function(
            #     func=get_user_timeline,
            #     name="twitter_get_user_timeline",
            #     description="Get a user's timeline (recent tweets). First-time users will be prompted to authorize. Input should be a dictionary with 'username', optional 'max_results', and optional 'user_id' keys.",
            # ),
        ]

        # Combine Arcade's Twitter tools with our custom wrappers
        return tools + custom_tools  # type: ignore

    except Exception as e:
        print(f"Failed to create Twitter tools: {e}")
        return None
