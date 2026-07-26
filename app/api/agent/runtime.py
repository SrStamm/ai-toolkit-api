import json
from typing import Any, List, Optional
import uuid
import structlog
import re

from .adapters.rag_adapter import QueryServiceAdapter, create_query_adapter
from .agent import Agent
from .schemas import ActionType, AgentState, EventType, RuntimeState
from .tool_runner import ToolRunner
from ..llamaindex_adapter.orchestrator import LlamaIndexOrchestrator
from ..retrieval_engine.ingestion_service import IngestionService
from ..retrieval_engine.service import get_rag_service
from ...application.llm.client import LLMClient, get_llm_client
from .session_memory import Message, get_session_memory, SessionMemory
from ...infrastructure.storage.qdrant_client import get_qdrant_store
from ...infrastructure.storage.hybrid_ai import get_hybrid_embeddign_service as get_hybrid_embedding_service

logger = structlog.get_logger()


class Runtime:
    def __init__(self,
        llm: LLMClient,
        rag: LlamaIndexOrchestrator | QueryServiceAdapter,
        vector_store: Any = None,
        ingestion_service: Any = None,
        ) -> None:

        vs = vector_store or get_qdrant_store()
        embed_svc = get_hybrid_embedding_service()
        ing_svc = ingestion_service or IngestionService(vector_store=vs, embed_service=embed_svc)
        self.tool_runner = ToolRunner(deps={
            "rag_orchestrator": rag,
            "llm_client": llm,
            "vector_store": vs,
            "ingestion_service": ing_svc,
        })
        self.session_memory: SessionMemory = get_session_memory()
        self.agent = Agent(llm)
        self._state: RuntimeState = RuntimeState.THINKING

    def _transition_to(self, new_state: RuntimeState, **metadata) -> str:
        self._state = new_state
        payload = {"state": new_state.value, **metadata}
        return self.emit_events(EventType.STATE_CHANGED, json.dumps(payload))

    async def execution_loop(
        self,
        state: AgentState,
        max_step: int = 5,
    ):
        for _ in range(max_step):
            yield self._transition_to(RuntimeState.THINKING)
            # Get decision from agent
            decision = await self.agent.decide(state)

            # Yield decision event
            yield self.emit_events(EventType.AGENT_DECISION, json.dumps(decision.model_dump()))

            if decision.action == ActionType.ASK_USER:
                yield self._transition_to(RuntimeState.WAITING_USER)

                # Router needs to ask the user a question (e.g., missing metadata).
                content = decision.args.get("message", "")
                self.session_memory.add(state.session_id, "assistant", content)
                yield self.emit_events(EventType.LLM_TOKEN, json.dumps({"token": content}))
                yield self.emit_events(EventType.DONE, json.dumps({
                    "usage": {},
                    "cost": {},
                    "model": "",
                    "provider": "",
                    "citations": state.citations,
                    "session_id": state.session_id,
                }))
                state.complete = True
                return  # Exit the generator cleanly, user needs to respond

            if decision.action == ActionType.FINAL_ANSWER:
                return

            if decision.action == ActionType.CALL_TOOL and decision.tool_name:
                yield self._transition_to(RuntimeState.EXECUTING_TOOL, tool=decision.tool_name)
                result = self.execute_tool(decision.tool_name, state, decision.args)

                # CRITICAL FIX: Pass metadata (e.g., task_id) to state
                state.apply(result)

                yield self.emit_events(EventType.TOOL_DONE, json.dumps({'tool': decision.tool_name, 'status': 'success'}))

                if result.complete:
                    content = result.output
                    self.session_memory.add(state.session_id, "assistant", content)
                    state.complete = True

                    yield self.emit_events(EventType.LLM_TOKEN, json.dumps({"token": content}))
                    yield self.emit_events(EventType.DONE, json.dumps({
                        "usage": {},
                        "cost": {},
                        "model": "",
                        "provider": "",
                        "citations": state.citations,
                        "session_id": state.session_id,
                        "metadata": result.metadata or {}
                    }))
                    yield self._transition_to(RuntimeState.COMPLETED)
                    return

                continue


    def execute_step(self):
        pass

    def execute_tool(self, tool_name: str, state: AgentState, args: dict | None = None):
        return self.tool_runner.run(tool_name, args, state)


    def emit_events(self, event: EventType, data: str):
        """Format SSE event."""
        return f"event: {event.value}\ndata: {data}\n\n"

    def _create_session_id(self) -> str:
        """Create a new session ID."""
        return str(uuid.uuid4())

    def resolve_file_context(
            self,
            history: List[Message],
            query: str,
            file_uuid: Optional[str] = None,
            filename: Optional[str] = None,
    ):
        # If a file was attached, prepend its info to the query so the
        # Router can see it and decide which tool to call.
        if file_uuid and filename:
            query = f"[Archivo adjunto: {filename} (UUID: {file_uuid})]\n\n{query}"

            return file_uuid, filename, query

        else:
            for msg in reversed(history):
                if msg.role == "user" and "[Archivo adjunto:" in msg.content:
                    match = re.search(
                        r'\[Archivo adjunto: (.+?) \(UUID: ([a-f0-9-]+)\)\]',
                        msg.content,
                    )
                    if match:
                        hist_filename = match.group(1)
                        hist_file_uuid = match.group(2)
                        query = (
                            f"[Archivo adjunto: {hist_filename} "
                            f"(UUID: {hist_file_uuid})]\n\n{query}"
                        )
                        file_uuid = hist_file_uuid
                        filename = hist_filename
                        return file_uuid, filename, query
                    return "", "", ""

        return "", "", ""

    async def stream_final_answer(self, state: AgentState):
        async for event in self.agent.generate_answer(state):
            if event.type == EventType.LLM_TOKEN:
                yield self.emit_events(EventType.LLM_TOKEN, json.dumps({'token': event.token}))

            elif event.type == EventType.DONE:
                self.session_memory.add(
                    state.session_id,
                    "assistant",
                    event.content
                )

                yield self.emit_events(EventType.DONE, json.dumps(event.metadata))

    async def run_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        domain: Optional[str] = None,
        file_uuid: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        try:
            if not session_id:
                session_id = self._create_session_id()

            self.session_memory.add(session_id, "user", query)
            history = self.session_memory.get_history(session_id)

            file_uuid, filename, query = self.resolve_file_context(
                history,
                query,
                file_uuid,
                filename,
            )

            state = AgentState(
                query=query,
                session_id=session_id,
                domain=domain,
                file_uuid=file_uuid,
                filename=filename,
            )
            state.history = history

            async for event in self.execution_loop(state):
                yield event

            if state.complete:
                return

            yield self._transition_to(RuntimeState.GENERATING)
            async for event in self.stream_final_answer(state):
                yield event
            yield self._transition_to(RuntimeState.COMPLETED)

        except Exception as e:
            logger.error("runtime_stream_error", error=str(e))
            yield self._transition_to(RuntimeState.FAILED, error=str(e))
            yield self.emit_events(EventType.DONE, json.dumps({
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
            }))


def create_runtimer(
    provider: str | None = None,
    model: str | None = None,
    use_rag_service: bool = False,  # Flag to use RAG service via adapter
) -> Runtime:
    """
    Factory function to create an Agent instance.
    """
    llm = get_llm_client(provider, model)

    # Initialize infrastructure dependencies
    vector_store = get_qdrant_store()
    embed_service = get_hybrid_embedding_service()
    ingestion_svc = IngestionService(vector_store=vector_store, embed_service=embed_service)

    # Use RAG service with adapter (retrieval_engine/)
    rag_service = get_rag_service()
    rag_adapter = create_query_adapter(rag_service)
    return Runtime(llm=llm, rag=rag_adapter, vector_store=vector_store, ingestion_service=ingestion_svc)
