import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from langchain.tools import StructuredTool
from langchain.tools import Tool
from langchain_arcade import ArcadeToolManager


def create_google_tools() -> Optional[List[Union[Tool, StructuredTool]]]:
    """Create and return Google tools using Arcade.

    This module requires proper Google authentication setup through the Arcade Dashboard:
    1. Create a Google Cloud project and configure OAuth consent screen
       - Set up the necessary API permissions (Calendar, Drive, etc.)
       - Set redirect URL to: https://cloud.arcade.dev/api/v1/oauth/callback
       - Create OAuth client ID and secret
    2. Configure in Arcade Dashboard:
       - Go to OAuth section and click "Add OAuth Provider"
       - Select Google provider
       - Enter your Google app's client ID and secret
       - Save the configuration

    Returns:
        Optional[List[Union[Tool, StructuredTool]]]: List of Google tools if ARCADE_API_KEY is available, None otherwise.
    """
    try:
        # Initialize the tool manager
        tool_manager = ArcadeToolManager()

        # Get Google tools
        tools = tool_manager.get_tools(toolkits=["Google"])

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

        def create_calendar_event(args: Union[Dict[str, Any], str]) -> str:
            """Create an event in Google Calendar.

            First-time users will be prompted to authorize through Google OAuth.

            Args:
                args: Dictionary containing:
                    - summary: Event title/summary
                    - start_datetime: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
                    - end_datetime: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
                    - description: (Optional) Event description
                    - location: (Optional) Event location
                    - attendees: (Optional) List of email addresses for attendees
                    - user_id: (Optional) User identifier for authentication
                  Or a string that will be parsed as JSON.

            Returns:
                str: Response message.
            """
            # Handle string input (convert to dict if possible)
            if isinstance(args, str):
                if args.strip():
                    try:
                        import json

                        args = json.loads(args)
                    except json.JSONDecodeError:
                        return "Error: Input must be a valid JSON string or dictionary"
                else:
                    return "Error: Required parameters missing (summary, start_datetime, end_datetime)"

            # Ensure args is a dictionary
            if not isinstance(args, dict):
                return "Error: Input must be a dictionary or valid JSON string"

            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Google.CreateEvent"

            try:
                check_auth(tool_name, user_id)

                # Prepare input with required fields
                input_data = {
                    "summary": args["summary"],
                    "start_datetime": args["start_datetime"],
                    "end_datetime": args["end_datetime"],
                }

                # Add optional fields if provided
                if "description" in args:
                    input_data["description"] = args["description"]
                if "location" in args:
                    input_data["location"] = args["location"]
                if "attendees" in args:
                    input_data["attendees"] = args["attendees"]

                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input=input_data,
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error creating calendar event: {str(e)}"

        def list_calendar_events(args: Union[Dict[str, Any], str]) -> str:
            """List events from Google Calendar.

            First-time users will be prompted to authorize through Google OAuth.

            Args:
                args: Dictionary containing:
                    - time_min: (Optional) Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
                    - time_max: (Optional) End time in ISO format (YYYY-MM-DDTHH:MM:SS)
                    - max_results: (Optional) Maximum number of events to return
                    - user_id: (Optional) User identifier for authentication
                  Or a string that will be parsed as JSON or treated as empty input.

            Returns:
                str: Response message containing calendar events.
            """
            # Handle string input (convert to dict if possible)
            if isinstance(args, str):
                if args.strip():
                    try:
                        import json

                        args = json.loads(args)
                    except json.JSONDecodeError:
                        # If string can't be parsed as JSON, use empty dict
                        args = {}
                else:
                    args = {}

            # Ensure args is a dictionary
            if not isinstance(args, dict):
                args = {}

            user_id = args.get("user_id", os.getenv("ARCADE_USER_ID"))
            tool_name = "Google.ListEvents"

            try:
                check_auth(tool_name, user_id)

                # Prepare input with optional fields
                input_data = {}
                if "time_min" in args:
                    input_data["time_min"] = args["time_min"]
                if "time_max" in args:
                    input_data["time_max"] = args["time_max"]
                if "max_results" in args:
                    input_data["max_results"] = args["max_results"]

                response = tool_manager.execute(  # type: ignore
                    tool_name=tool_name,
                    input=input_data,
                    user_id=user_id,
                )
                return str(response)
            except Exception as e:
                return f"Error listing calendar events: {str(e)}"

        # Create custom tool wrappers
        custom_tools: List[Union[Tool, StructuredTool]] = [
            # Tool.from_function(
            #     func=create_calendar_event,
            #     name="google_create_calendar_event",
            #     description="Create an event in Google Calendar. First-time users will be prompted to authorize. Input should be a dictionary with 'summary', 'start_datetime', 'end_datetime', optional 'description', optional 'location', optional 'attendees', and optional 'user_id' keys.",
            # ),
            # Tool.from_function(
            #     func=list_calendar_events,
            #     name="google_list_calendar_events",
            #     description="List events from Google Calendar. First-time users will be prompted to authorize. Input should be a dictionary with optional 'time_min', optional 'time_max', optional 'max_results', and optional 'user_id' keys.",
            # ),
        ]

        # Combine Arcade's Google tools with our custom wrappers
        return tools + custom_tools  # type: ignore

    except Exception as e:
        print(f"Failed to create Google tools: {e}")
        return None
