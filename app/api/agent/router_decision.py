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

    async def get_decision(self, state: AgentState) -> Decision:
        """Async method to get LLM decision.

        Args:
            state: Current agent state

        Returns:
            Decision with action to take
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
        
        # Pass full tool result to prompt (critical for tool-based decisions)
        # We truncate only if extremely long to avoid prompt overflow, but metadata is usually short
        MAX_RESULT_LEN = 1000
        tool_res = state.last_tool_result or "None"
        if len(tool_res) > MAX_RESULT_LEN:
            tool_res = tool_res[:MAX_RESULT_LEN] + "... [truncated]"
            
        system_content = PROMPT_ROUTING_SYSTEM.format(
            tool_list=tools,
            context=bool(state.context),
            tool_execution_count=state.tool_execution_count,
            last_tool=state.last_tool or "None",
            last_tool_result=tool_res,
        )
        
        # Include history in the user message if available
        full_query = state.query
        if history_context:
            full_query = f"{history_context}\n\nCurrent question: {state.query}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": full_query}
        ]
        
        response = await self.llm.generate_content_with_messages_async(messages=messages)
        raw = response.content.strip()
        
        logger.info(
            "router_decision",
            step=state.tool_execution_count + 1,
            query_preview=state.query[:100],
            has_context=bool(state.context),
            has_history=bool(state.history),
            raw_response=raw,
        )
        
        try:
            decision_json = json.loads(raw)
            
            # Prevent repeated context retrieval
            if decision_json.get('action') == "retrieve_context" and state.context:
                logger.warning("Preventing repeated context retrieval")
                return Decision(action=ActionType.FINAL_ANSWER)
            
            # Prevent repeated tool execution
            if decision_json.get('action') == "call_tool":
                tool_name = decision_json.get("tool_name")
                if tool_name and tool_name == state.last_tool:
                    logger.warning(
                        "Preventing repeated tool execution",
                        tool=tool_name,
                        last_tool=state.last_tool
                    )
                    return Decision(action=ActionType.FINAL_ANSWER)
            
            return Decision(
                action=ActionType(decision_json.get("action", "final_answer")),
                tool_name=decision_json.get("tool_name"),
                args=decision_json.get("args", {})
            )
        except Exception:
            logger.warning(f"Invalid JSON from router: {raw}")
            return Decision(action=ActionType.FINAL_ANSWER)
