from typing import Literal

import ell
from fargs.components import ClaimsExtractor
from fargs.components import CommunitySummarizer
from fargs.components import EntityExtractor
from fargs.components import GraphLoader
from fargs.components import RelationshipExtractor
from fargs.components.claims import CLAIM_EXTRACTION_MESSAGE
from fargs.components.communities import CommunityReport
from fargs.components.graph import SUMMARIZE_NODE_MESSAGE
from fargs.components.graph import SUMMARIZE_NODE_PROMPT
from fargs.components.relationships import RELATIONSHIP_EXTRACTION_MESSAGE
from fargs.components.relationships import RelationshipOutput


class TerraEntityExtractor(EntityExtractor):
    def _construct_function(self):
        @ell.complex(
            model="gpt-4o-mini",
            temperature=0,
            response_format=self._output_model,
        )
        def extract_entities(node_text: str):
            return [
                ell.system(self.prompt),
                ell.user(node_text),
            ]

        return extract_entities


class TerraRelationshipExtractor(RelationshipExtractor):
    def _construct_function(self):
        @ell.complex(
            model="gpt-4o-mini",
            temperature=0,
            response_format=RelationshipOutput,
        )
        def extract_relationships(entities_json: str, text_unit: str):
            return [
                ell.system(self.prompt),
                ell.user(
                    RELATIONSHIP_EXTRACTION_MESSAGE.format(
                        entities_json=entities_json,
                        text_unit=text_unit,
                    )
                ),
            ]

        return extract_relationships


class TerraClaimsExtractor(ClaimsExtractor):
    def _construct_function(self):
        @ell.complex(
            model="gpt-4o-mini",
            temperature=0,
            response_format=self._output_model,
        )
        def extract_claims(entities_json: str, text_unit: str):
            return [
                ell.system(self.prompt),
                ell.user(
                    CLAIM_EXTRACTION_MESSAGE.format(
                        entities_json=entities_json,
                        text_unit=text_unit,
                    )
                ),
            ]

        return extract_claims


class TerraCommunitySummarizer(CommunitySummarizer):
    def _construct_function(self):
        @ell.complex(
            model="gpt-4o",
            temperature=0,
            response_format=CommunityReport,
        )
        def generate_community_report(community_text: str):
            return [
                ell.system(self.prompt),
                ell.user(community_text),
            ]

        return generate_community_report


class TerraGraphLoader(GraphLoader):
    def _construct_function(self):
        @ell.complex(model="gpt-4o-mini", temperature=0)
        def summarize_node(
            node_type: Literal["entity", "relation"],
            title: str,
            description: str,
        ):
            return [
                ell.system(SUMMARIZE_NODE_PROMPT),
                ell.user(
                    SUMMARIZE_NODE_MESSAGE.format(
                        type=node_type, title=title, description=description
                    )
                ),
            ]

        return summarize_node
