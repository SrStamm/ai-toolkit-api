from fastapi import APIRouter, Depends
from .agent import get_agent, Agent
from ...api.rag.schemas import QueryRequest

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/ask-custom")
def custom_query_llama(
    query: QueryRequest,
    serv: Agent = Depends(get_agent)
):
    return serv.agent(query=query.text)
