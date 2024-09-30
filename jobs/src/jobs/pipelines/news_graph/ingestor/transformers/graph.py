import asyncio
from typing import List

from llama_index.core.graph_stores import EntityNode
from llama_index.core.graph_stores import Relation
from llama_index.core.graph_stores.types import KG_NODES_KEY
from llama_index.core.graph_stores.types import KG_RELATIONS_KEY
from llama_index.core.schema import BaseNode
from llama_index.core.schema import TransformComponent
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.postgresql import select as pg_select

from jobs.database import database_session
from jobs.database.schemas import NewsEntitySchema
from jobs.database.schemas import NewsRelationshipSchema
from jobs.pipelines.news_graph.models import Entity
from jobs.pipelines.news_graph.models import Relationship


class GraphTransformer(TransformComponent):
    PROCESS_LOCK = asyncio.Lock()
    DATABASE_LOCK = asyncio.Lock()

    def __call__(self, nodes: List[BaseNode], **kwargs) -> List[BaseNode]:
        return asyncio.run(self.acall(nodes, **kwargs))

    async def acall(self, nodes: List[BaseNode], **kwargs) -> List[BaseNode]:
        node_tasks = [self.transform_node(node, **kwargs) for node in nodes]
        return await asyncio.gather(*node_tasks)

    async def transform_node(self, node: BaseNode, **kwargs) -> BaseNode:
        async with self.PROCESS_LOCK:
            entities = node.metadata.pop("entities", None)
            relationships = node.metadata.pop("relationships", None)

            entity_tasks = [
                self.construct_entity_node(node, entity) for entity in entities
            ]
            entity_nodes = await asyncio.gather(*entity_tasks)

            relationship_tasks = [
                self.construct_relation_node(node, relationship)
                for relationship in relationships
            ]
            relationship_nodes = await asyncio.gather(*relationship_tasks)

            node.metadata[KG_NODES_KEY] = entity_nodes
            node.metadata[KG_RELATIONS_KEY] = relationship_nodes
            return node

    async def construct_entity_node(
        self, parent_node: BaseNode, entity: Entity
    ) -> EntityNode:
        async with self.DATABASE_LOCK:
            async with database_session() as session:
                entity_id = entity.name.replace('"', " ")

                existing_entity = await session.execute(
                    pg_select(NewsEntitySchema).where(NewsEntitySchema.id == entity_id)
                )
                existing_entity = existing_entity.scalar_one_or_none()

                entity_values = {
                    "id": entity_id,
                    "name": entity.name,
                    "entity_type": entity.entity_type.value,
                    "description": (
                        f"{existing_entity.description} {entity.description}"
                        if existing_entity
                        else entity.description
                    ),
                    "attributes": (
                        {
                            **existing_entity.attributes,
                            **{attr.name: attr.value for attr in entity.attributes},
                        }
                        if existing_entity
                        else {attr.name: attr.value for attr in entity.attributes}
                    ),
                }

                insert_stmt = pg_insert(NewsEntitySchema).values(**entity_values)
                update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "name": insert_stmt.excluded.name,
                        "entity_type": insert_stmt.excluded.entity_type,
                        "description": insert_stmt.excluded.description,
                        "attributes": insert_stmt.excluded.attributes,
                    },
                )
                await session.execute(update_stmt)
                await session.commit()

        return EntityNode(
            name=entity_values["name"],
            label=entity_values["entity_type"],
            properties={
                "source": parent_node.doc_id,
                "description": entity_values["description"],
                **entity_values["attributes"],
            },
        )

    async def construct_relation_node(
        self, parent_node: BaseNode, relation: Relationship
    ) -> Relation:
        async with self.DATABASE_LOCK:
            async with database_session() as session:
                relation_id = (
                    f"{relation.source_entity.replace('"', " ")}_"
                    f"{relation.relation_type}_"
                    f"{relation.target_entity.replace('"', " ")}"
                )

                existing_relation = await session.execute(
                    pg_select(NewsRelationshipSchema).where(
                        NewsRelationshipSchema.id == relation_id
                    )
                )
                existing_relation = existing_relation.scalar_one_or_none()

                relation_values = {
                    "id": relation_id,
                    "source_entity": relation.source_entity.replace('"', " "),
                    "target_entity": relation.target_entity.replace('"', " "),
                    "relation_type": relation.relation_type,
                    "description": (
                        f"{existing_relation.description} {relation.description}"
                        if existing_relation
                        else relation.description
                    ),
                    "strength": (
                        (existing_relation.strength + relation.strength) / 2
                        if existing_relation
                        else relation.strength
                    ),
                }

                insert_stmt = pg_insert(NewsRelationshipSchema).values(
                    **relation_values
                )
                update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "source_entity": insert_stmt.excluded.source_entity,
                        "target_entity": insert_stmt.excluded.target_entity,
                        "relation_type": insert_stmt.excluded.relation_type,
                        "description": insert_stmt.excluded.description,
                        "strength": insert_stmt.excluded.strength,
                    },
                )
                await session.execute(update_stmt)
                await session.commit()

        return Relation(
            label=relation_values["relation_type"],
            source_id=relation_values["source_entity"],
            target_id=relation_values["target_entity"],
            properties={
                "source": parent_node.doc_id,
                "description": relation_values["description"],
                "strength": relation_values["strength"],
            },
        )
