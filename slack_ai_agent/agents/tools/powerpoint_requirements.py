"""PowerPoint requirements definition tool."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from langchain.tools import StructuredTool


def format_requirements(requirements: Dict) -> str:
    """Format requirements into a readable string.

    Args:
        requirements: Dictionary containing requirements

    Returns:
        str: Formatted requirements string
    """
    formatted = "# パワーポイント作成要件\n\n"

    # タイトル
    if "title" in requirements:
        formatted += f"## タイトル\n{requirements['title']}\n\n"

    # 目的
    if "purpose" in requirements:
        formatted += f"## 目的\n{requirements['purpose']}\n\n"

    # 対象者
    if "audience" in requirements:
        formatted += f"## 対象者\n{requirements['audience']}\n\n"

    # 主要なトピック
    if "topics" in requirements and requirements["topics"]:
        formatted += "## 主要なトピック\n"
        for topic in requirements["topics"]:
            formatted += f"- {topic}\n"
        formatted += "\n"

    # スタイルと形式
    if "style" in requirements:
        formatted += f"## スタイルと形式\n{requirements['style']}\n\n"

    # 特別な要望
    if "special_requests" in requirements:
        formatted += f"## 特別な要望\n{requirements['special_requests']}\n\n"

    return formatted


def parse_requirements(requirements_text: str) -> Dict:
    """Parse requirements text into a structured dictionary.

    Args:
        requirements_text: Text containing requirements

    Returns:
        Dict: Structured requirements
    """
    requirements: Dict[str, Any] = {
        "title": "",
        "purpose": "",
        "audience": "",
        "topics": [],  # 明示的にList[str]として扱う
        "style": "",
        "special_requests": "",
    }

    # Simple parsing logic - can be improved
    lines = requirements_text.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for section headers
        if line.startswith("# ") or line.startswith("## "):
            section = line.lstrip("#").strip().lower()
            if "タイトル" in section or "title" in section:
                current_section = "title"
            elif "目的" in section or "purpose" in section:
                current_section = "purpose"
            elif "対象" in section or "audience" in section:
                current_section = "audience"
            elif "トピック" in section or "topic" in section:
                current_section = "topics"
            elif "スタイル" in section or "style" in section:
                current_section = "style"
            elif "要望" in section or "request" in section:
                current_section = "special_requests"
            continue

        # Add content to the current section
        if current_section:
            if current_section == "topics" and line.startswith("-"):
                requirements["topics"].append(line[1:].strip())
            elif current_section == "topics":
                # If it's not a bullet point but we're in topics section,
                # treat each line as a separate topic
                requirements["topics"].append(line)
            else:
                if requirements[current_section]:
                    requirements[current_section] += "\n" + line
                else:
                    requirements[current_section] = line

    return requirements


def validate_requirements(requirements: Dict) -> List[str]:
    """Validate requirements and return a list of issues.

    Args:
        requirements: Dictionary containing requirements

    Returns:
        List[str]: List of validation issues
    """
    issues = []

    # Check for missing required fields
    if not requirements.get("title"):
        issues.append("タイトルが設定されていません")

    if not requirements.get("purpose"):
        issues.append("目的が設定されていません")

    if not requirements.get("topics"):
        issues.append("トピックが設定されていません")

    return issues


def create_requirements_definition(
    user_input: str, existing_requirements: Optional[str] = None
) -> Dict:
    """Create a requirements definition for PowerPoint generation.

    Args:
        user_input: User input text
        existing_requirements: Existing requirements text (optional)

    Returns:
        Dict: Dictionary containing the requirements definition and validation results
    """
    # If there are existing requirements, parse them
    existing_req_dict = {}
    if existing_requirements:
        existing_req_dict = parse_requirements(existing_requirements)

    # Extract requirements from user input
    new_req_dict = parse_requirements(user_input)

    # Merge requirements, with new requirements taking precedence
    merged_requirements = {**existing_req_dict, **new_req_dict}

    # Validate the requirements
    issues = validate_requirements(merged_requirements)

    # Format the requirements
    formatted_requirements = format_requirements(merged_requirements)

    return {
        "requirements": merged_requirements,
        "formatted_requirements": formatted_requirements,
        "validation_issues": issues,
        "is_valid": len(issues) == 0,
    }


# Create the requirements definition tool
create_requirements_definition_tool = StructuredTool.from_function(
    func=create_requirements_definition,
    name="create_requirements_definition",
    description="Create a requirements definition for PowerPoint generation based on user input.",
)
