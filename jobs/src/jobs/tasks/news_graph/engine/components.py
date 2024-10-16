import ell
from fargs.components import ClaimsExtractor
from fargs.components import CommunitySummarizer
from fargs.components import EntityExtractor
from fargs.components import RelationshipExtractor
from fargs.components.claims import CLAIM_EXTRACTION_MESSAGE
from fargs.components.communities import CommunityReport
from fargs.components.relationships import RELATIONSHIP_EXTRACTION_MESSAGE

from jobs.config import openrouter_extra_body


class TerraEntityExtractor(EntityExtractor):
    def _construct_function(self):
        @ell.complex(
            model="qwen/qwen-2.5-72b-instruct",
            temperature=0,
            response_format={"type": "json_object"},
            extra_body=openrouter_extra_body,
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
            model="qwen/qwen-2.5-72b-instruct",
            temperature=0,
            response_format={"type": "json_object"},
            extra_body=openrouter_extra_body,
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
            model="qwen/qwen-2.5-72b-instruct",
            temperature=0,
            response_format={"type": "json_object"},
            extra_body=openrouter_extra_body,
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
            model="openai/gpt-4o",
            temperature=0,
            response_format=CommunityReport,
            extra_body=openrouter_extra_body,
        )
        def generate_community_report(community_text: str):
            return [
                ell.system(self.prompt),
                ell.user(community_text),
            ]

        return generate_community_report
