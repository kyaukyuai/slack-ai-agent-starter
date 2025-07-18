import operator
from typing import Annotated
from typing import List
from typing import Literal
from typing import TypedDict

from pydantic import BaseModel
from pydantic import Field


class SearchQuery(BaseModel):
    search_query: str = Field(..., description="Query for web search.")


class Queries(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )


class Section(BaseModel):
    headline: str = Field(
        description="Headline (小見出し) for this section of the article.",
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section.",
    )
    research: bool = Field(
        description="Whether to perform web research for this section of the article."
    )
    content: str = Field(description="The content of the section.")
    quotes: List[dict] = Field(
        default_factory=list,
        description="Notable quotes from sources related to this section, with text, source, and relevance.",
    )
    references: List[dict] = Field(
        default_factory=list,
        description="References and citations for this section with title, url, and metadata.",
    )


class Reference(BaseModel):
    title: str = Field(description="Title of the reference.")
    url: str = Field(description="URL of the reference.")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the reference, such as author, published date, etc.",
    )


class SectionOutput(BaseModel):
    content: str = Field(description="The main content of the section.")
    quotes: List[dict] = Field(
        description="Notable quotes related to this section (3-5 items), with text, source, and relevance."
    )
    references: List[Reference] = Field(
        description="References and citations for this section."
    )


class Sections(BaseModel):
    sections: List[Section] = Field(
        description="Sections of the report.",
    )


class InputContent(BaseModel):
    url: str
    title: str
    markdown: str
    metadata: dict


class ReportState(TypedDict):
    input: InputContent  # 入力情報を構造化
    queries: list[SearchQuery]  # 検索クエリリスト
    title: str  # Title (記事全体のタイトル)
    feedback_on_report_plan: str  # Feedback on the report plan
    sections: list[Section]  # List of article sections
    completed_sections: Annotated[list, operator.add]  # Send() API key
    report_sections_from_research: (
        str  # String of any completed sections from research to write final sections
    )
    final_report: str  # Final report


class ReportStateInput(TypedDict):
    url: str  # URL of the web content to analyze


class ReportStateOutput(TypedDict):
    final_report: str  # Final report


class SectionState(TypedDict):
    url: str  # URL of the web content to analyze
    url_content: str  # Content of the URL
    section: Section  # Report section
    search_iterations: int  # Number of search iterations done
    search_queries: list[SearchQuery]  # List of search queries
    source_str: str  # String of formatted source content from web search
    report_sections_from_research: (
        str  # String of any completed sections from research to write final sections
    )
    completed_sections: list[
        Section
    ]  # Final key we duplicate in outer state for Send() API


class Feedback(BaseModel):
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    follow_up_queries: List[SearchQuery] = Field(
        description="List of follow-up search queries.",
    )


class SectionOutputState(TypedDict):
    completed_sections: list[
        Section
    ]  # Final key we duplicate in outer state for Send() API
