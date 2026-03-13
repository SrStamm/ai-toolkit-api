from ..llamaindex.orchrestator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)

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
        Decide how to answer the query.

        Options:
        - rag
        - direct

        Use rag if the question requires information from the knowledge base.

        Query:
        {query}

        Answer with one word.
        """

        return self.llm.generate_content(prompt).content

    def agent(self, query: str):
        decision = self.router(query)

        if decision == "rag":
            return self.rag.custom_query(query=query)

        return self.llm.generate_content(query)


def create_agent() -> Agent:
    return Agent(
        llm=get_llm_client(),
        rag=get_orchestrator()
    )

def get_agent() -> Agent:
    return create_agent()

