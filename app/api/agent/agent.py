"""
Agent determinístico con tool registry.

Decide qué tool usar según la query del usuario.
"""

import structlog
import uuid
import json

from .session_memory import get_session_memory, Message, SessionMemory
from .schemas import AgentResponse
from .tools import ToolRegistry
from .schemas import AgentState
from .prompt import PROMPT_ROUTING_SYSTEM, PROMP_GENERATE_ANSWER
from ..llamaindex_adapter.orchestrator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)
from ...domain.exceptions import ToolNotFoundError

logger = structlog.get_logger()


class Agent:
    """
    Agente determinístico que usa LLM para decidir qué tool ejecutar.
    """

    def __init__(self, llm: LLMClient, rag: LlamaIndexOrchestrator):
        # Inicializar tools lazily
        ToolRegistry.initialize()

        self.tools = ToolRegistry.list_tools()
        self.deps = {"rag_orchestrator": rag, "llm_client": llm}
        self.llm = llm
        self.session_memory: SessionMemory = get_session_memory()

    def _create_session_id(self) -> str:
        """Create a new session ID."""
        return str(uuid.uuid4())

    def _build_context(self, query: str, history: list[Message]) -> str:
        """Build context string from conversation history."""
        if not history:
            return query

        history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in history])

        return f"""Last conversation:
        {history_str}
        Query: {query}"""

    def build_tool_list(self) -> str:
        """Build human-readable list of available tools for the router prompt."""
        return "\n".join(
            f"- {name}: {defn.description} (params: {list(defn.parameters['properties'].keys())})"
            for name, defn in self.tools.items()
        )

    def execute(self, tool_name: str, query: str, context_str: str = ""):
        """Execute a tool by name."""
        if tool_name not in self.tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")

        tool_def = self.tools[tool_name]

        relevant_deps = {
            k: v for k, v in self.deps.items() if k in tool_def.dependencies
        }

        kwargs = {"query": query, "context": context_str, **relevant_deps}

        return tool_def.handler(**kwargs)

    def router(self, state: AgentState) -> str:
        """Decide which tool to use based on the query."""
        # Get available tools
        tools = self.build_tool_list()

        # Create prompt
        prompt = PROMPT_ROUTING_SYSTEM.format(
            query=state.query,
            tool_list=tools
        )

        logger.info("DEBUG_PROMPT_ROUTER", prompt=prompt)

        raw = self.llm.generate_content(prompt).content.strip()

        logger.info("DEBUG_DECISION_ROUTER", raw=raw)

        try:
            decision_json = json.loads(raw)
            return decision_json.get("action", "final_answer")

        except Exception:
            logger.warning(f"Invalid JSON from router: {raw}")
            return "final_answer"

    def generate_answer(self, state: AgentState) -> str:
        prompt = PROMP_GENERATE_ANSWER.format(question=state.query)

        if state.context:
            prompt = prompt + f"Context: {state.context}"

        response = self.llm.generate_content(prompt).content.strip().lower()

        return response

    def agent_loop(self, query: str):
        # Create state
        state = AgentState(query=query)

        # Loop for agent
        for step in range(3):
            # Agent make a decision
            decision = self.router(state)

            if decision == "retrieve_context":
                context = self.execute("retrieve_context", state.query)
                state.context = context

            elif decision == "final_answer":
                return self.generate_answer(state)


def create_agent() -> Agent:
    """Factory function to create an Agent instance."""
    return Agent(llm=get_llm_client(), rag=get_orchestrator())


def get_agent() -> Agent:
    """Get or create agent singleton."""
    return create_agent()
