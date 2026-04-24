from fastapi import APIRouter, Depends
from .schemas import QueryAgentRequest
from .agent import get_agent, Agent

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/agent-loop")
def agent_loop(
        query: QueryAgentRequest,
        serv: Agent = Depends(get_agent)
):
    return serv.agent_loop(
        query=query.text,
        session_id=query.session_id
    )
