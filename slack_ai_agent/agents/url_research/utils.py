import json
import re

from .models import Section


def format_sections(sections: list[Section]) -> str:
    """Format a list of sections into a string"""
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
{"=" * 60}
Section {idx}: {section.headline}
{"=" * 60}
Description:
{section.description}
Requires Research:
{section.research}

Content:
{section.content if section.content else "[Not yet written]"}

"""
    return formatted_str


def get_config_value(value):
    """
    Helper function to handle both string and enum cases of configuration values
    """
    return value if isinstance(value, str) else value.value


def extract_json_from_response(response_text: str) -> str:
    """JSONブロックを抽出する共通関数"""
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    else:
        # ```json がない場合は、テキスト全体をJSONとして解析を試みる
        return response_text


def parse_json_with_fallback(json_str: str, default_value=None):
    """JSONを解析し、失敗した場合はデフォルト値を返す共通関数"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return default_value
