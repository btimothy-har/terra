# Credits to the LlamaIndex Cookbook https://docs.llamaindex.ai/en/stable/examples/cookbooks/GraphRAG_v2/

import json
import os
from collections import defaultdict

import networkx as nx
from graspologic.partition import hierarchical_leiden
from llama_index.core.schema import Document
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore


class GraphRAGStore(Neo4jPropertyGraphStore):
    max_cluster_size = 10
    entity_community_map = None

    def generate_communities(self):
        nx_graph = self._create_nx_graph()
        community_hierarchical_clusters = hierarchical_leiden(
            nx_graph, max_cluster_size=self.max_cluster_size
        )
        self.entity_community_map, community_info = self._collect_community_info(
            nx_graph, community_hierarchical_clusters
        )
        return self._transform_communities(community_info)

    def _create_nx_graph(self):
        """Converts internal graph representation to NetworkX graph."""
        nx_graph = nx.Graph()
        triplets = self.get_triplets()
        for entity1, relation, entity2 in triplets:
            nx_graph.add_node(entity1.name)
            nx_graph.add_node(entity2.name)
            nx_graph.add_edge(
                relation.source_id,
                relation.target_id,
                relationship=relation.label,
                description=relation.properties["description"],
            )
        return nx_graph

    def _collect_community_info(self, nx_graph, clusters):
        """
        Collect information for each node based on their community,
        allowing entities to belong to multiple clusters.
        """
        entity_info = defaultdict(set)
        community_info = defaultdict(list)

        for item in clusters:
            node = item.node
            cluster_id = item.cluster

            entity_info[node].add(cluster_id)

            for neighbor in nx_graph.neighbors(node):
                edge_data = nx_graph.get_edge_data(node, neighbor)
                if edge_data:
                    detail = {
                        "relationship": (
                            f"{node} -> {edge_data['relationship']} -> {neighbor}"
                        ),
                        "description": edge_data["description"],
                    }
                    community_info[cluster_id].append(detail)

        entity_info = {k: list(v) for k, v in entity_info.items()}
        return dict(entity_info), dict(community_info)

    def _transform_communities(self, community_info):
        communities = dict()

        for community_id, details in community_info.items():
            communities[community_id] = Document(
                text="\n".join([json.dumps(d) for d in details]),
                metadata={
                    "community_id": community_id,
                },
            )

        return communities


graph_store = GraphRAGStore(
    username="neo4j",
    password=os.getenv("NEO4J_PASSWORD"),
    url="bolt://neo4j:7687",
    refresh_schema=False,
)
