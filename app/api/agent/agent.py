from ..llamaindex.orchrestator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)
import structlog
import json


logger = structlog.get_logger()

class Agent:
    def __init__(
            self,
            llm: LLMClient,
            rag: LlamaIndexOrchestrator
    ):
        self.llm = llm
        self.rag = rag

    def router(self, query: str) -> str:
        prompt = f"""
        You are a routing system.

        Decide how the question should be answered.

        Options:
        rag -> if the answer should come from the knowledge base
        direct -> if the LLM can answer using general knowledge

        Knowledge base contains:
        - technical documentation
        - books
        - internal content

        Query:
        {query}

        Answer ONLY with:
        rag
        or
        direct
        """

        decision = self.llm.generate_content(prompt).content

        logger.info("Router raw output", output=decision)

        if "rag" in decision:
            return "rag"

        return "direct"

    def execute(self, decision: str, query: str):
        if decision == "rag":
            return self.rag.custom_query(query=query)

        return self.llm.generate_content(query)

    def agent(self, query: str):
        decision = self.router(query)
        logger.info("Agent decision", query=query, decision=decision)

        return self.execute(decision, query)


def create_agent() -> Agent:
    return Agent(
        llm=get_llm_client(),
        rag=get_orchestrator()
    )

def get_agent() -> Agent:
    return create_agent()

