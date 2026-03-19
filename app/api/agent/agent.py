from .prompt import PROMPT_ROUTING_SYSTEM
from .model import DirectTool, RagTool
from ..llamaindex.orchrestator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)
import structlog


logger = structlog.get_logger()

class Agent:
    def __init__(
        self,
        llm: LLMClient,
        rag: LlamaIndexOrchestrator
    ):
        self.llm = llm
        self.rag = rag
        self.tools = self._build_tools()

    def _build_tools(self):
        return {
            "rag": RagTool(self.rag),
            "direct": DirectTool(self.llm)
        }

    def router(self, query: str) -> str:
        prompt = PROMPT_ROUTING_SYSTEM.format(query=query)

        decision = self.llm.generate_content(prompt).content

        logger.info("Router raw output", output=decision)

        return decision

    def execute(self, decision: str, query: str):
        if decision not in self.tools:
            raise ValueError(f"Tool '{decision}' dosn't exist")

        tool = self.tools[decision]
        return tool.execute(query)

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

