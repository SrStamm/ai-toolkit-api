"""
Agent determinístico con tool registry.

Orquestador que coordina ToolRunner y Router para ejecutar acciones.
"""

import structlog
import json

from .schemas import AgentEvent, AgentState, Decision, EventType
from .prompt import PROMPT_GENERATE_ANSWER
from .router_decision import Router
from .tools import ToolRegistry
from ..llamaindex_adapter.orchestrator import LLMClient

logger = structlog.get_logger()


def extract_answer_from_json(content: str) -> str:
    """
    Extract answer from JSON wrapper if present.
    Handles various JSON formats: {"answer": "..."}, {"response": "..."}, etc.
    Also handles code block wrappers like ```json\n...\n```
    """
    import re
    
    if not content:
        return content

    # Remove markdown code block wrapper if present
    cleaned = content.strip()
    # Regex to remove starting ```json or ```text or ```
    cleaned = re.sub(r'^```(?:json|text)?\n?', '', cleaned)
    # Remove trailing ```
    cleaned = re.sub(r'```$', '', cleaned)
    cleaned = cleaned.strip()
    
    # Try to parse as JSON
    if cleaned.startswith('{') and cleaned.endswith('}'):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                # Common field names that might contain the answer
                for key in ['answer', 'response', 'text', 'content', 'message']:
                    if key in parsed and isinstance(parsed[key], str):
                        return parsed[key].strip()
                # If single key, use its value
                if len(parsed) == 1:
                    value = list(parsed.values())[0]
                    if isinstance(value, str):
                        return value.strip()
        except json.JSONDecodeError:
            pass
    
    # Return original content if not JSON or parsing failed
    return content.strip()


class Agent:
    """
    Agente determinístico que usa LLM para decidir qué tool ejecutar.
    
    Ahora actúa como orchestrator que coordina ToolRunner y Router.
    """

    def __init__(self, llm: LLMClient):
        self.router = Router(llm_client=llm)
        self.router.tools = ToolRegistry.list_tools()
        self.llm = llm

    async def decide(self, state: AgentState) -> Decision:
        return await self.router.get_decision(state)


    async def generate_answer(self, state: AgentState):
        # Generate final answer with streaming + buffering
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
        
        # Buffer for tokens
        token_buffer = ""
        BUFFER_SIZE = 30  # chars
        
        async for token, final_response in self.llm.generate_content_with_messages_stream(messages=messages):
            if token:
                token_buffer += token

                # Send buffer when full or at punctuation
                if len(token_buffer) >= BUFFER_SIZE or token in '.!?\n':
                    yield AgentEvent(
                        type=EventType.LLM_TOKEN,
                        token=token_buffer
                    )

                    token_buffer = ""

            if final_response:
                # Send remaining buffer
                if token_buffer:
                    yield AgentEvent(
                        type=EventType.LLM_TOKEN, 
                        token=token_buffer,
                    )
                    token_buffer = ""

                # Parse answer from JSON wrapper if present (robust parser)
                content = token_buffer.strip() if token_buffer else ""
                if not content and final_response.content:
                    content = final_response.content.strip()
                # Apply robust JSON extraction
                content = extract_answer_from_json(content)

                # Merge tool metadata (e.g., task_id from ingestion) into response metadata
                # Convert TokenUsage to simple dicts for JSON serialization
                usage_dict = {}
                if final_response.usage:
                    # Manually create dict to avoid 'TokenUsage not JSON serializable'
                    usage_dict = {
                        'prompt_tokens': final_response.usage.prompt_tokens,
                        'completion_tokens': final_response.usage.completion_tokens,
                        'total_tokens': final_response.usage.total_tokens,
                    }

                cost_dict = {}
                if final_response.cost:
                    cost_dict = {
                        'total_cost': final_response.cost.total_cost,
                    }

                final_metadata = {
                    'usage': usage_dict,
                    'cost': cost_dict,
                    'model': final_response.model,
                    'provider': final_response.provider,
                    'citations': state.citations,  # Include accumulated citations
                    'session_id': state.session_id,
                }

                # If last tool returned specific metadata (like task_id), include it
                if state.last_tool_metadata:
                    final_metadata.update(state.last_tool_metadata)
                    if state.last_tool_metadata.get("task_id"):
                        final_metadata['task_id'] = state.last_tool_metadata['task_id']
                    final_metadata['status'] = state.last_tool_metadata.get('status', 'processing')

                yield AgentEvent(
                    type=EventType.DONE,
                    content=content,
                    metadata=final_metadata
                )

                break


def create_agent(llm: LLMClient) -> Agent:
    return Agent(llm=llm)

