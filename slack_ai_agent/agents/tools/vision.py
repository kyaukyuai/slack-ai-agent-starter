"""Vision-related tools for the LangGraph implementation."""

import base64
import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence

import requests  # type: ignore
from langchain_core.tools import BaseTool
from langchain_core.tools import StructuredTool
from pydantic import BaseModel


def encode_image(image_path: str) -> str:
    """Encode image to base64 string.

    Args:
        image_path: Path to the image file

    Returns:
        str: Base64 encoded image string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


class VisionInput(BaseModel):
    """Input schema for vision tool."""

    prompt: str
    image_paths: List[str]


async def vision(prompt: str, image_paths: Sequence[str]) -> str:
    """Pass multiple images to the multimodal AI to get results.

    Args:
        prompt: The text prompt to analyze the images
        image_paths: List of paths to image files

    Returns:
        str: AI's analysis of the images based on the prompt

    Raises:
        requests.exceptions.RequestException: If the API request fails
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": 300,
    }
    for image_path in image_paths:
        base64_image = encode_image(image_path)
        payload["messages"][0]["content"].append(  # type: ignore
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "low",
                },
            }
        )
    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )
    response_json: Dict[str, Any] = response.json()
    return response_json["choices"][0]["message"]["content"]


def create_vision_tool() -> Optional[BaseTool]:
    """Create vision-related tools.

    Returns:
        Optional[BaseTool]: Vision tool if OPENAI_API_KEY is available, None otherwise
    """
    if os.getenv("OPENAI_API_KEY"):
        return StructuredTool(
            name="vision",
            description="Pass multiple images to the multimodal AI to get results",
            func=vision,
            args_schema=VisionInput,  # type: ignore
        )
    return None
