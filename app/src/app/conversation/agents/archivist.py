import requests
from config import API_ENDPOINT
from langchain_core.tools import tool
from typing_extensions import Annotated

from .base import BaseAgent
from .prompts.archivist import ARCHIVIST_PROMPT


class ArchivistAgent(BaseAgent):
    """
    Arthur, Archivist
    - Proficient in translating context into queries to search a conversation archive.
    - Skilled in extracting relevant information from the archive.
    - Has access to a conversational archive of past reports and agent conversations.
    """

    def __init__(self):
        super().__init__(
            name="Arthur",
            title="Archivist",
            sys_prompt=ARCHIVIST_PROMPT,
            tools=[ArchivistAgent.search_archive],
        )

        self.tool_model = self.model.bind_tools(
            list(self.tools.values()), tool_choice="search_archive"
        )

    @tool
    @staticmethod
    def search_archive(
        query: Annotated[str, "The query that to search for in the archive."],
        reason: Annotated[str, "Explain the reason for choosing this tool."],
    ) -> str:
        """
        Query the historical archive for information. This is information that other
        agents have prepared and archived.
        """

        search_request = requests.get(
            url=f"{API_ENDPOINT}/threads/context/search",
            params={"query": query, "top_k": 6},
        )
        search_request.raise_for_status()
        search_docs = search_request.json()

        if len(search_docs) == 0:
            return "No relevant information was found in the archive."

        doc_return = [f"**{doc['agent']}**\n{doc['content']}" for doc in search_docs]
        return "\n\n".join(doc_return)
