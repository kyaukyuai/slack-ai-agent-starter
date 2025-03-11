"""Marp generation tool."""

import os
from datetime import datetime
from typing import Dict
from typing import List

import pytz  # type: ignore
from langchain.tools import StructuredTool


def get_current_jst_time() -> str:
    """Get the current time in JST format.

    Returns:
        str: Current time in JST format (YYYYMMDD_HHMMSS)
    """
    jst = pytz.timezone("Asia/Tokyo")
    current_time = datetime.now(jst)
    return current_time.strftime("%Y%m%d_%H%M%S")


def create_marp_markdown(title: str, slides: List[Dict]) -> str:
    """Create a Marp markdown presentation.

    Args:
        title: The title of the presentation
        slides: List of slide data

    Returns:
        str: Path to the created Marp markdown file
    """
    # Create the marp markdown content with frontmatter
    markdown_content = """---
marp: true
theme: default
paginate: true
header: ""
footer: ""
---

"""

    # Process each slide
    for i, slide_data in enumerate(slides):
        try:
            # Add slide separator if not the first slide
            if i > 0:
                markdown_content += "\n---\n\n"

            # Add the markdown content for this slide
            markdown_content += slide_data.get("markdown_content", "")
        except Exception as e:
            # If there's an error creating a slide, add a simple error slide
            print(f"Error creating slide: {str(e)}")
            if i > 0:
                markdown_content += "\n---\n\n"
            markdown_content += (
                f"# Error: {slide_data.get('header', 'Slide Error')}\n\n"
            )
            markdown_content += f"Error creating slide: {str(e)}\n\n"

    # Save the markdown file
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = get_current_jst_time()
    filename = f"{title.replace(' ', '_')}_{timestamp}.md"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return file_path


def generate_marp(topic: str, content: Dict) -> str:
    """Generate a Marp presentation.

    Args:
        topic: The topic of the presentation
        content: Dictionary containing the presentation content

    Returns:
        str: Path to the created Marp markdown file
    """
    title = content.get("title", topic)
    slides = content.get("pages", [])

    return create_marp_markdown(title, slides)


# Create the Marp tool
create_marp_tool = StructuredTool.from_function(
    func=generate_marp,
    name="generate_marp",
    description="Generate a Marp presentation based on the provided topic and content. Returns the path to the created markdown file.",
)
