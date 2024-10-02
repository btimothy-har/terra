# ruff: noqa: E501

FILTER_LANGUAGE_PROMPT = """
You are an expert in language classification. Given the title and text of a news article, determine if it is in English.

If the title and text are not in the same language, return False.

Provide your response in JSON following this schema: {schema_text}
"""
