# Prompt to generate search queries to help with planning the report
report_planner_query_writer_instructions = """You are an expert technical writer, helping to plan a report.

<Report topic>
{topic}
</Report topic>

<Report organization>
{report_organization}
</Report organization>

<Task>
Your goal is to generate {number_of_queries} search queries that will help gather comprehensive information for planning the report sections.

The queries should:

1. Be related to the topic of the report
2. Help satisfy the requirements specified in the report organization

Make the queries specific enough to find high-quality, relevant sources while covering the breadth needed for the report structure.
</Task>
"""
