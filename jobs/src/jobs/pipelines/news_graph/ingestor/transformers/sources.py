from llama_index.core.graph_stores.types import KG_NODES_KEY
from llama_index.core.graph_stores.types import KG_RELATIONS_KEY
from llama_index.core.schema import TransformComponent


class SourcesTransformer(TransformComponent):
    def __call__(self, nodes, **kwargs):
        for node in nodes:
            node.metadata.pop(KG_NODES_KEY, None)
            node.metadata.pop(KG_RELATIONS_KEY, None)
            node.metadata.pop("claims", None)
        return nodes
