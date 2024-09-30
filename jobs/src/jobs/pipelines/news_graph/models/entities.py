from enum import Enum

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class DefaultEntityTypes(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    INDUSTRY = "industry"
    LOCATION = "location"
    LANGUAGE = "language"
    CURRENCY = "currency"
    GEOPOLITICAL_ENTITY = "geopolitical_entity"
    NORP = "nationality_or_religious_or_political_group"
    LEGAL = "legal_documents_or_laws_or_treaties"
    ART = "work_of_art"
    PRODUCT_OR_SERVICE = "product_or_service"
    EVENT = "event"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class EntityAttribute(BaseModel):
    name: str = Field(
        title="Name",
        description="The name of the attribute (e.g. date of birth).",
    )
    value: str = Field(
        title="Value",
        description=(
            "The value of the attribute (e.g. 1970-01-01). "
            "Dates should be in the format YYYY-MM-DD.  "
        ),
    )


class Entity(BaseModel):
    name: str = Field(
        title="Name",
        description=(
            "The name of the entity, in upper case. DO NOT use abbreviations. "
        ),
    )
    entity_type: DefaultEntityTypes = Field(
        title="Type",
        description=(
            "The type of the entity. Select from the list of valid "
            "types provided to you in your instructions. If none of the types match, "
            "you may use other."
        ),
    )
    description: str = Field(
        title="Description",
        description=(
            "Comprehensive, single-paragraph description of the "
            "entity's attributes and activities."
        ),
    )
    attributes: list[EntityAttribute] = Field(
        title="Attributes",
        description=(
            "List of attributes of the entity. "
            "Attributes are additional details or characteristics that "
            "provide context about the entity. "
            "Attributes should be relatively permanent in nature. "
            "For example, a date of birth is an attribute, but age is not. "
        ),
    )

    def __str__(self):
        return f"{self.name}: {self.description}"

    @field_validator("name", mode="before")
    @classmethod
    def capitalize_fields(cls, value):
        return value.upper()

    @field_validator("entity_type", mode="before")
    @classmethod
    def validate_entity_type(cls, value):
        if str(value).lower() not in [t.value for t in DefaultEntityTypes]:
            return DefaultEntityTypes.OTHER.value
        return str(value).lower()

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["entity_type"] = data["entity_type"].value
        return data
