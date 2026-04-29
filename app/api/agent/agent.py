"""
Agent determinístico con tool registry.

Orquestador que coordina ToolRunner y Router para ejecutar acciones.
"""

from typing import Optional
import structlog
import uuid
import json

from .session_memory import get_session_memory, SessionMemory
from .schemas import AgentResponse, AgentState, ActionType
from .tools import ToolRegistry
from .prompt import PROMPT_GENERATE_ANSWER
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

        # Add user query to session history
        self.session_memory.add(session_id, "user", query)

        # Get conversation history for context
        history = self.session_memory.get_history(session_id)
        state.history = history

        # Loop for agent - with step counter
        step = 0
        while True:
            step += 1

            # Get decision from router
            decision = self.router.get_decision(state)

            logger.info(
                "agent_step",
                step=step,
                decision_action=decision.action.value,
                decision_tool=decision.tool_name,
                decision_args=decision.args,
                session_id=session_id,
            )

            # Handle FINAL_ANSWER
            if decision.action == ActionType.FINAL_ANSWER:
                logger.info(
                    "agent_finished",
                    step=step,
                    total_tool_executions=state.tool_execution_count,
                    session_id=session_id,
                )
                break

            # Handle RETRIEVE_CONTEXT
            if decision.action == ActionType.RETRIEVE_CONTEXT:
                result = self.tool_runner.run(
                    "retrieve_context",
                    decision.args,
                    state
                )
                # Guardar contexto obtenido
                state.context = result.output
                logger.info(
                    "DEBUG_SET_CONTEXT",
                    context_preview=result.output[:100],
                    state_context_after=state.context[:100] if state.context else "None",
                    session_id=session_id,
                )
                state.set_last_tool("retrieve_context", result.output)
                logger.info(
                    "agent_tool_executed",
                    step=step,
                    tool="retrieve_context",
                    args=decision.args,
                    result_preview=result.output[:300],
                    session_id=session_id,
                )
                continue

            # Handle CALL_TOOL
            if decision.action == ActionType.CALL_TOOL:
                result = self.tool_runner.run(
                    decision.tool_name,
                    decision.args,
                    state
                )
                # Registrar trazabilidad de tool
                state.set_last_tool(decision.tool_name, result.output)
                logger.info(
                    "agent_tool_executed",
                    step=step,
                    tool=decision.tool_name,
                    args=decision.args,
                    result_preview=result.output[:300],
                    session_id=session_id,
                )
                continue

        return self.generate_answer(state)

    def generate_answer(self, state: AgentState) -> AgentResponse:
        """Genera la respuesta final usando el LLM."""
        messages: list[dict] = []

        # System message with the prompt template
        system_prompt = PROMPT_GENERATE_ANSWER
        messages.append({"role": "system", "content": system_prompt})

        # Add conversation history as messages (excluding the last user message to avoid duplication)
        if state.history:
            for msg in state.history[:-1]:
                messages.append({"role": msg.role, "content": msg.content})

        # User message with context (if available) and the question
        user_content = state.query
        if state.context:
            user_content = f"Context from knowledge base:\n{state.context}\n\nQuestion: {state.query}"
        
        messages.append({"role": "user", "content": user_content})

        response = self.llm.generate_content_with_messages(messages=messages)
        
        # Verificar que la respuesta no esté vacía
        if not response.content or not response.content.strip():
            logger.warning("Empty LLM response, using fallback")
            parsed = {"answer": state.context or "No se pudo generar una respuesta."}
        else:
            try:
                parsed = json.loads(response.content)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from LLM: {e}, using fallback")
                parsed = {"answer": state.context or "No se pudo generar una respuesta."}

        logger.info(
            "llm_final_response",
            answer=parsed["answer"][:200] + "..." if len(parsed["answer"]) > 200 else parsed["answer"],
            model=response.model,
            provider=response.provider,
            usage_prompt=response.usage.prompt_tokens,
            usage_completion=response.usage.completion_tokens,
            usage_total=response.usage.total_tokens,
            cost_usd=round(response.cost.total_cost, 6),
            session_id=state.session_id,
        )

        # Save assistant response to session history
        self.session_memory.add(
            state.session_id,
            "assistant",
            parsed["answer"]
        )

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

    async def agent_loop_stream(self, query: str, session_id: Optional[str] = None):
        """
        Streaming version of agent_loop.

        Yields SSE events:
        - agent_decision: Router decision
        - tool_start: Tool execution started
        - tool_done: Tool execution completed
        - llm_token: LLM response token
        - done: Final response with metadata
        """

        def sse_event(event: str, data: str) -> str:
            """Format SSE event."""
            return f"event: {event}\ndata: {data}\n\n"

        if not session_id:
            session_id = self._create_session_id()

        state = AgentState(query=query, session_id=session_id)
        self.session_memory.add(session_id, "user", query)
        history = self.session_memory.get_history(session_id)
        state.history = history

        step = 0
        while True:
            step += 1
            decision = await self.router._get_decision_async(state)

            # Yield decision event
            yield sse_event("agent_decision", json.dumps(decision.model_dump()))
            
            if decision.action == ActionType.FINAL_ANSWER:
                yield sse_event("done", json.dumps({'session_id': session_id, 'step': step}))
                break
            
            if decision.action == ActionType.RETRIEVE_CONTEXT:
                yield sse_event("tool_start", json.dumps({'tool': 'retrieve_context'}))
                
                result = self.tool_runner.run(
                    "retrieve_context",
                    decision.args,
                    state
                )
                # Guardar contexto obtenido
                state.context = result.output
                state.set_last_tool("retrieve_context", result.output)
                
                yield sse_event("tool_done", json.dumps({'tool': 'retrieve_context', 'status': 'success'}))
                continue
            
            if decision.action == ActionType.CALL_TOOL:
                yield sse_event("tool_start", json.dumps({'tool': decision.tool_name}))
                
                result = self.tool_runner.run(
                    decision.tool_name,
                    decision.args,
                    state
                )
                state.set_last_tool(decision.tool_name, result.output)
                
                yield sse_event("tool_done", json.dumps({'tool': decision.tool_name, 'status': 'success'}))
                continue
        
        # Generate final answer with streaming
        messages: list[dict] = []
        system_prompt = PROMPT_GENERATE_ANSWER
        messages.append({"role": "system", "content": system_prompt})
        
        if state.history:
            for msg in state.history[:-1]:
                messages.append({"role": msg.role, "content": msg.content})
        
        user_content = state.query
        if state.context:
            user_content = f"Context from knowledge base:\n{state.context}\n\nQuestion: {state.query}"
        messages.append({"role": "user", "content": user_content})
        
        accumulated_answer = ""
        async for token, final_response in self.llm.generate_content_with_messages_stream(
            messages=messages
        ):
            if token:
                accumulated_answer += token
                yield sse_event("llm_token", json.dumps({'token': token}))
            
            if final_response:
                # Strip the "answer" wrapper since we're streaming tokens directly
                # The model should return just the content now
                accumulated_answer = accumulated_answer.strip()
                if accumulated_answer.startswith('{"answer":'):
                    try:
                        parsed = json.loads(accumulated_answer)
                        accumulated_answer = parsed.get("answer", accumulated_answer)
                    except:
                        pass
                
                self.session_memory.add(
                    state.session_id,
                    "assistant",
                    accumulated_answer
                )
                
                yield sse_event("done", json.dumps({
                    'session_id': state.session_id,
                    'answer': accumulated_answer,
                    'usage': final_response.usage.__dict__ if final_response.usage else {},
                    'cost': final_response.cost.__dict__ if final_response.cost else {},
                    'model': final_response.model,
                    'provider': final_response.provider
                }))
                break


def create_agent(
    provider: str | None = None,
    model: str | None = None,
) -> Agent:
    """Factory function to create an Agent instance."""
    return Agent(llm=get_llm_client(provider, model), rag=get_orchestrator())


def get_agent() -> Agent:
    """Get or create agent singleton."""
    return create_agent()
