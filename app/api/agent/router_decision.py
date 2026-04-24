"""
Router: Decide qué acción tomar usando LLM.

Componente separado del Agent para manejar la decisión de qué herramienta usar.
"""

import json
import structlog
from typing import Any

from .schemas import Decision, AgentState, ActionType
from .prompt import PROMPT_ROUTING_SYSTEM

logger = structlog.get_logger()


class Router:
    """Decide qué acción tomar usando LLM."""

    def __init__(self, llm_client: Any):
        self.llm = llm_client
        self.tools = None  # Se establece desde Agent
    
    def _build_tool_list(self) -> str:
        """Construye lista legible de herramientas para el prompt."""
        if not self.tools:
            return "No tools available"
        
        return "\n".join(
            f"- {name}: {defn.description}"
            for name, defn in self.tools.items()
        )
    
    def get_decision(self, state: AgentState) -> Decision:
        """Obtiene decisión del LLM sobre qué acción tomar.
        
        Args:
            state: Estado actual del agente
             
        Returns:
            Decision con la acción a tomar
        """
        tools = self._build_tool_list()
        
        # Build conversation history for context
        history_context = ""
        if state.history:
            prev_messages = []
            for msg in state.history:
                if msg.role == "user":
                    prev_messages.append(f"User: {msg.content}")
                elif msg.role == "assistant":
                    prev_messages.append(f"Assistant: {msg.content}")
            if prev_messages:
                history_context = "\n\nPrevious conversation:\n" + "\n".join(prev_messages)
        
        system_content = PROMPT_ROUTING_SYSTEM.format(
            tool_list=tools,
            context=bool(state.context)
        )
        
        # Include history in the user message if available
        full_query = state.query
        if history_context:
            full_query = f"{history_context}\n\nCurrent question: {state.query}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": full_query}
        ]
        
        raw = self.llm.generate_content_with_messages(messages=messages).content.strip()
        logger.info("DEBUG_ROUTER", raw=raw)
        
        try:
            decision_json = json.loads(raw)
            
            # Prevenir recuperación repetida de contexto
            if decision_json.get('action') == "retrieve_context" and state.context:
                logger.warning("Preventing repeated context retrieval")
                return Decision(action=ActionType.FINAL_ANSWER)
            
            return Decision(
                action=ActionType(decision_json.get("action", "final_answer")),
                tool_name=decision_json.get("tool_name"),
                args=decision_json.get("args", {})
            )
        except Exception:
            logger.warning(f"Invalid JSON from router: {raw}")
            return Decision(action=ActionType.FINAL_ANSWER)
