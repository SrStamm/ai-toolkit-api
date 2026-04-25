from fastapi import APIRouter, Request
from .schemas import QueryAgentRequest
from .agent import create_agent

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/agent-loop")
def agent_loop(query: QueryAgentRequest, request: Request):
    agent = create_agent(
        provider=request.headers.get("x-llm-provider"),
        model=request.headers.get("x-llm-model"),
    )
    return agent.agent_loop(
        query=query.text,
        session_id=query.session_id
    )
