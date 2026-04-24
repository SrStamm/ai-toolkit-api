"""
Agent determinístico con tool registry.

Decide qué tool usar según la query del usuario.
"""

from typing import Optional
import structlog
import uuid
import json

from .session_memory import get_session_memory, SessionMemory, Message
from .schemas import AgentResponse, AgentState, Decision
from .tools import ToolRegistry
from .prompt import PROMPT_ROUTING_SYSTEM, PROMPT_GENERATE_ANSWER
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

    def execute(self, tool_name: str, state: AgentState, tool_args: dict | None = None):
        if tool_name not in self.tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")

        tool_def = self.tools[tool_name]

        # deps
        relevant_deps = {
            k: v for k, v in self.deps.items()
            if k in tool_def.dependencies
        }

        # filter state data by tool_params
        tool_params = tool_def.parameters.get("properties", {}).keys()
        state_data = state.model_dump()
        filtered_state = {
            k: v for k, v in state_data.items()
            if k in tool_params
        }

        # Merge con prioridad:
        final_kwargs = {
            **(tool_args or {}),
            **filtered_state,
            **relevant_deps
        }

        return tool_def.handler(**final_kwargs)


    def router(self, state: AgentState) -> Decision:
        """Decide which tool to use based on the query."""
        # Get available tools
        tools = self.build_tool_list()

        # Build messages: system with prompt + user with query
        system_content = PROMPT_ROUTING_SYSTEM.format(
            tool_list=tools,
            context=True if state.context else False
        )
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": state.query}
        ]

        # Call LLM
        raw = self.llm.generate_content_with_messages(messages=messages).content.strip()
        logger.info("DEBUG_DECISION_ROUTER", raw=raw, query=state.query)

        try:
            decision_json = json.loads(raw)

            # Prevent repeated context retrieval
            if decision_json.get('action') == "retrieve_context" and state.context:
                logger.warning("Preventing repeated context retrieval")
                return Decision(action="final_answer")

            return Decision(
                action=decision_json.get("action", "final_answer"),
                args=decision_json.get("args")
            )

        except Exception:
            logger.warning(f"Invalid JSON from router: {raw}")
            return Decision(action="final_answer")

    def generate_answer(self, state: AgentState) -> AgentResponse:
        messages: list[dict] = []

        # System message with the prompt template
        system_prompt = PROMPT_GENERATE_ANSWER
        messages.append({"role": "system", "content": system_prompt})

        # User message with context (if available) and the question
        user_content = state.query
        if state.context:
            user_content = f"Context from knowledge base:\n{state.context}\n\nQuestion: {state.query}"
        
        messages.append({"role": "user", "content": user_content})

        response = self.llm.generate_content_with_messages(messages=messages)
        parsed = json.loads(response.content)

        logger.info("DEBUG_RESPONSE_LLM", response=str(response))

        return AgentResponse(
            output=parsed["answer"],
            session_id=state.session_id,
            metadata={
                'usage': response.usage,
                'cost': response.cost,
                'model': response.model,
                'provider': response.provider
            }
        )

    def agent_loop(self, query: str, session_id: Optional[str] = None):
        # Create session_id if not exists
        if not session_id:
            session_id = self._create_session_id()

        # Create state
        state = AgentState(query=query, session_id=session_id)

        # Loop for agent
        for step in range(3):
            # Agent make a decision
            decision = self.router(state)

            if decision.action == "retrieve_context":
                context = self.execute(
                    "retrieve_context",
                    state=state,
                    tool_args=decision.args
                )
                state.context = context

            return self.generate_answer(state)


def create_agent() -> Agent:
    """Factory function to create an Agent instance."""
    return Agent(llm=get_llm_client(), rag=get_orchestrator())


def get_agent() -> Agent:
    """Get or create agent singleton."""
    return create_agent()
