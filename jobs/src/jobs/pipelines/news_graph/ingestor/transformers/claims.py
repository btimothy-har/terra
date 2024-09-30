from llama_index.core.schema import Document
from llama_index.core.schema import TransformComponent


def construct_claim_document(parent_node, claim):
    document = Document(
        text=claim.description,
        metadata={
            "source": parent_node.doc_id,
            "subject": claim.claim_subject,
            "object": claim.claim_object,
            "type": claim.claim_type.value,
            "status": claim.status.value,
            "period": claim.period,
            "references": claim.sources,
        },
    )
    document.excluded_embed_metadata_keys = ["source", "references"]
    document.excluded_llm_metadata_keys = ["source"]
    return document


class ClaimsTransformer(TransformComponent):
    def __call__(self, nodes, **kwargs):
        all_claims = []
        for node in nodes:
            claims = node.metadata.pop("claims", None)

            claim_docs = [construct_claim_document(node, claim) for claim in claims]
            all_claims.extend(claim_docs)
        return all_claims
