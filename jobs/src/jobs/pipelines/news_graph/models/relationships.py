from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY

from jobs.database.schemas import Base


class Relationship(BaseModel):
    source_entity: str = Field(title="Source", description="The source entity.")
    target_entity: str = Field(title="Target", description="The target entity.")

    relation_type: str = Field(
        title="Type",
        description="The type of relationship between the source and target entities.",
    )

    description: str = Field(
        title="Description",
        description=(
            "Single-paragraph description of the relationship between the source and "
            "target entities."
        ),
    )
    strength: float = Field(
        title="Strength",
        description=(
            "A numeric float in 2 decimal places from 0.0 to 1.0 indicating the "
            "strength of the relationship."
        ),
    )

    @field_validator("source_entity", "target_entity", mode="before")
    @classmethod
    def capitalize_entity(cls, value):
        return value.upper()

    def __str__(self):
        return f"{self.source_entity} > {self.relation_type} > {self.target_entity}"


class NewsRelationshipSchema(Base):
    __tablename__ = "relationships"
    __table_args__ = {"schema": "news"}

    id = Column(String, primary_key=True, nullable=False)
    source_entity = Column(String, nullable=False)
    target_entity = Column(String, nullable=False)
    relation_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    strength = Column(Float, nullable=False)
    sources = Column(ARRAY(String))
