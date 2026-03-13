from fastapi import APIRouter, Depends
from ...api.rag.schemas import QueryRequest
from .agent import get_agent, Agent

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/ask-custom")
def custom_query_llama(
    query: QueryRequest,
    serv: Agent = Depends(get_agent)
):
    return serv.agent(
        query=query.text,
    )
