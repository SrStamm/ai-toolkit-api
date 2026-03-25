import structlog

from .tools.tools_registry import TOOL_REGISTRY
from .prompt import PROMPT_ROUTING_SYSTEM
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
        self.tools = TOOL_REGISTRY.copy()
        self.deps = {
            "rag_orchestrator": rag,
            "llm_client": llm
        }
        self.llm = llm

    def build_tool_list(self) -> str:
        return "\n".join([
            f"- {name}: {defn.description} (params: {list(defn.parameters['properties'].keys())})"
            for name, defn in TOOL_REGISTRY.items()
        ])

    def execute(self, tool_name: str, query: str):
        tool_def = self.tools.get(tool_name)

        if not tool_def:
            raise ValueError(f"Tool '{tool_name}' not found")

        relevant_deps = {
            k: v for k, v in self.deps.items()
            if k in tool_def.dependencies
        }

        kwargs = {"query": query, **relevant_deps}

        return tool_def.handler(**kwargs)

    def router(self, query: str) -> str:
        tools = self.build_tool_list()

        prompt = PROMPT_ROUTING_SYSTEM.format(query=query, tool_list=tools)

        decision = self.llm.generate_content(prompt).content
        decision = decision.strip().lower()

        if "rag" in decision:
            return "rag"
        elif "direct" in decision:
            return "direct"

        raise ValueError(f"Invalid router output: {decision}")

    def agent(self, query: str):
        decision = self.router(query)
        logger.info(
            "Tool execution",
            tool=decision,
            query=query
        )

        return self.execute(tool_name=decision, query=query)


def create_agent() -> Agent:
    return Agent(
        llm=get_llm_client(),
        rag=get_orchestrator()
    )

def get_agent() -> Agent:
    return create_agent()

