# ruff: noqa: E501

NEWS_LANGUAGE_PROMPT = """
You are an expert in language classification. Given the title and text of a news article, determine if it is in English.

If the title and text are not in the same language, return False.

Respond in the following JSON schema: {schema_text}
"""
