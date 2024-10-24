from fargs import Fargs
from llama_index.core.ingestion import DocstoreStrategy

from jobs.tasks.news.graph.config import PROJECT_NAME
from jobs.tasks.news.graph.config import embeddings
from jobs.tasks.news.graph.config import splitter

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

fargs = Fargs(
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
        "model": "qwen/qwen-2.5-72b-instruct",
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
fargs._components["entities"] = TerraEntityExtractor
fargs._components["relationships"] = TerraRelationshipExtractor
fargs._components["claims"] = TerraClaimsExtractor
fargs._components["communities"] = TerraCommunitySummarizer
fargs._components["graph"] = TerraGraphLoader
