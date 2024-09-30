# ruff: noqa: E501

EXTRACT_ENTITIES_PROMPT = """
### YOUR GOAL ###
You will be presented with a piece of text. Your task is to identify key named entities present in the text, and any relevant attributes.

Entities are defined as an explicitly named object or concept that has a distinct identity and meaning.

The date today is {current_date}. You may use this information to help identify entities, but should not be treated as an entity itself.

### INSTRUCTIONS ###
From the text provided, identify the named entities. For each identified entity, extract the following information:
- name: Name of the entity, capitalized.
- entity_type: The type of the entity.
- description: Comprehensive description of the entity's attributes and activities.
- attributes: List of attributes of the entity.

Provide your response in in JSON format following the schema:
{output_schema}
"""
