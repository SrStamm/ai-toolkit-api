import structlog

from .prompt import PROMPT_ROUTING_SYSTEM
from .model import DirectTool, RagTool, ToolResponse
from ..llamaindex.orchrestator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)


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
        decision = decision.strip().lower()

        if "rag" in decision:
            return "rag"
        elif "direct" in decision:
            return "direct"

        raise ValueError(f"Invalid router output: {decision}")

    def execute(self, decision: str, query: str):
        tool = self.tools.get(decision)

        if not tool:
            raise ValueError(f"Tool '{decision}' doesn't exist")

        try:
            return tool.execute(query)
        except Exception as e:
            logger.error("Tool execution failed", error=str(e))
            return ToolResponse(
                output="Something went wrong",
                metadata={"error":str(e)}
            )

    def agent(self, query: str):
        decision = self.router(query)
        logger.info(
            "Tool execution",
            tool=decision,
            query=query
        )

        return self.execute(decision, query)


def create_agent() -> Agent:
    return Agent(
        llm=get_llm_client(),
        rag=get_orchestrator()
    )

def get_agent() -> Agent:
    return create_agent()

