"""
Agent determinístico con tool registry.

Decide qué tool usar según la query del usuario.
"""

import structlog
import uuid

from app.api.agent.session_memory import get_session_memory, Message, SessionMemory
from app.api.agent.schemas import AgentResponse
from app.api.agent.tools import ToolRegistry
from app.api.agent.prompt import PROMPT_ROUTING_SYSTEM
from app.api.llamaindex.orchestrator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)
from app.domain.exceptions import ToolNotFoundError

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

    def router(self, query: str) -> str:
        """Decide which tool to use based on the query."""
        tools = self.build_tool_list()

        prompt = PROMPT_ROUTING_SYSTEM.format(query=query, tool_list=tools)

        decision = self.llm.generate_content(prompt).content
        decision = decision.strip().lower()

        if "rag" in decision:
            return "rag"
        elif "direct" in decision:
            return "direct"

        # Fallback: si el modelo no devuelve algo esperado, default a direct
        logger.warning(
            f"Router returned unexpected output: {decision}, defaulting to direct"
        )
        return "direct"

    def agent(self, query: str, session_id: str | None = None):
        """Main agent loop: route query to appropriate tool and return response."""
        # Create a session_id if not exists
        if not session_id:
            session_id = self._create_session_id()

        # Get history for session
        history = self.session_memory.get_history(session_id)

        # Build query with the context
        enriched_query = self._build_context(query, history)

        # Add user message
        self.session_memory.add(session_id, "user", query)

        # Router
        decision = self.router(enriched_query)
        result = self.execute(tool_name=decision, query=enriched_query)

        # Add ai message
        self.session_memory.add(session_id, "assistant", result.output)

        logger.info("Tool execution", tool=decision, query=enriched_query)

        return AgentResponse(
            output=result.output, session_id=session_id, metadata=result.metadata or {}
        )


def create_agent() -> Agent:
    """Factory function to create an Agent instance."""
    return Agent(llm=get_llm_client(), rag=get_orchestrator())


def get_agent() -> Agent:
    """Get or create agent singleton."""
    return create_agent()
