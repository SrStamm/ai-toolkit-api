"""
Agent determinístico con tool registry.

Orquestador que coordina ToolRunner y Router para ejecutar acciones.
"""

from typing import Optional
import structlog
import uuid
import json

from .session_memory import get_session_memory, SessionMemory, Message
from .schemas import AgentResponse, AgentState, Decision, ActionType
from .tools import ToolRegistry
from .prompt import PROMPT_ROUTING_SYSTEM, PROMPT_GENERATE_ANSWER
from .tool_runner import ToolRunner
from .router_decision import Router
from ..llamaindex_adapter.orchestrator import (
    LLMClient,
    LlamaIndexOrchestrator,
    get_orchestrator,
    get_llm_client,
)

logger = structlog.get_logger()


class Agent:
    """
    Agente determinístico que usa LLM para decidir qué tool ejecutar.
    
    Ahora actúa como orchestrator que coordina ToolRunner y Router.
    """

    def __init__(self, llm: LLMClient, rag: LlamaIndexOrchestrator):
        # Inicializar componentes
        self.tool_runner = ToolRunner(deps={"rag_orchestrator": rag, "llm_client": llm})
        self.router = Router(llm_client=llm)
        self.router.tools = ToolRegistry.list_tools()
        self.llm = llm
        self.session_memory: SessionMemory = get_session_memory()

    def _create_session_id(self) -> str:
        """Create a new session ID."""
        return str(uuid.uuid4())

    def agent_loop(self, query: str, session_id: Optional[str] = None):
        """Loop principal del agente.
        
        Coordina ToolRunner y Router para ejecutar acciones hasta llegar a FINAL_ANSWER.
        """
        # Create session_id if not exists
        if not session_id:
            session_id = self._create_session_id()

        # Create state
        state = AgentState(query=query, session_id=session_id)

        # Loop for agent
        while True:
            # Get decision from router
            decision = self.router.get_decision(state)

            # Handle FINAL_ANSWER
            if decision.action == ActionType.FINAL_ANSWER:
                break

            # Handle RETRIEVE_CONTEXT
            if decision.action == ActionType.RETRIEVE_CONTEXT:
                state.context = self.tool_runner.run(
                    "retrieve_context",
                    decision.args,
                    state
                )
                continue

            # Handle CALL_TOOL
            if decision.action == ActionType.CALL_TOOL:
                result = self.tool_runner.run(
                    decision.tool_name,
                    decision.args,
                    state
                )
                state.add_tool_result(result)
                continue

        return self.generate_answer(state)

    def generate_answer(self, state: AgentState) -> AgentResponse:
        """Genera la respuesta final usando el LLM."""
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


def create_agent() -> Agent:
    """Factory function to create an Agent instance."""
    return Agent(llm=get_llm_client(), rag=get_orchestrator())


def get_agent() -> Agent:
    """Get or create agent singleton."""
    return create_agent()
