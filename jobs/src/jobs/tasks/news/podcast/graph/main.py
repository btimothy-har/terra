from fargs import Fargs
from llama_index.core.ingestion import DocstoreStrategy

from ..config import PROJECT_NAME
from ..config import embeddings
from ..config import splitter
from .components import TerraClaimsExtractor
from .components import TerraCommunitySummarizer
from .components import TerraEntityExtractor
from .components import TerraGraphLoader
from .components import TerraRelationshipExtractor
from .stores import graph_store
from .stores import index_communities_store
from .stores import nodes_store
from .stores import raw_communities_store
from .types import ClaimTypes
from .types import EntityTypes

graph_engine = Fargs(
    project_name=PROJECT_NAME,
    pre_split_strategy=splitter,
    embedding_strategy=embeddings,
    graph_store=graph_store,
    nodes_vector_store=nodes_store,
    community_vector_store=index_communities_store,
    extraction_llm_model={
        "model": "gpt-4o-mini",
        "temperature": 0,
    },
    summarization_config={
        "docstore": raw_communities_store,
        "docstore_strategy": DocstoreStrategy.UPSERTS_AND_DELETE,
    },
    summarization_llm_model={
        "model": "gpt-4o",
        "temperature": 0,
    },
    excluded_embed_metadata_keys=[
        "doc_id",
        "entities",
        "relationships",
        "claims",
        "url",
        "author",
        "authors",
        "publish_date",
        "sentiment",
    ],
    excluded_llm_metadata_keys=["doc_id", "entities", "relationships", "claims"],
    entity_types=EntityTypes,
    claim_types=ClaimTypes,
)
graph_engine._components["entities"] = TerraEntityExtractor
graph_engine._components["relationships"] = TerraRelationshipExtractor
graph_engine._components["claims"] = TerraClaimsExtractor
graph_engine._components["communities"] = TerraCommunitySummarizer
graph_engine._components["graph"] = TerraGraphLoader
