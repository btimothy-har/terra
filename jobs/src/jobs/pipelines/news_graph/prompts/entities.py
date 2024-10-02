# ruff: noqa: E501

EXTRACT_ENTITIES_PROMPT = """
### YOUR GOAL ###
You will be presented with a piece of text. Your task is to identify key named entities present in the text, and any relevant attributes.

Entities are defined as an explicitly named object or concept that has a distinct identity and meaning.
Entities should ALWAYS be identified with proper nouns, using full and complete versions, unabbreviated.

EXAMPLES:
- "She" is not a proper noun, but "Sally" is.
- "U.S." should be identified as "United States of America".
- "NATO" should be identified as "North Atlantic Treaty Organization".

The date today is {current_date}. You may use this information to help identify entities, but should not be treated as an entity itself.

### INSTRUCTIONS ###
From the text provided, identify the named entities. For each identified entity, extract the following information:
- name: Name of the entity, capitalized.
- entity_type: The type of the entity.
- description: Comprehensive description of the entity's attributes and activities.
- attributes: List of attributes of the entity.

Provide your response in JSON following this schema:
{output_schema}
"""
