from .prompt import PROMPT_ROUTING_SYSTEM
from .model import build_tool_registry
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

    def router(self, query: str) -> str:
        prompt = PROMPT_ROUTING_SYSTEM.format(query=query)

        decision = self.llm.generate_content(prompt).content

        logger.info("Router raw output", output=decision)

        return decision

    def execute(self, decision: str, query: str):
        tools = build_tool_registry()

        if decision not in tools:
            raise ValueError(f"Tool '{decision}' dosn't exist")

        tool = tools[decision]
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

