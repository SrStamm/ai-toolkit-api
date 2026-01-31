from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from .schemas import IngestRequest, QueryRequest, QueryResponse
from .service import RAGService, get_rag_service

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post(
    "/ingest",
    description="""
    It ingests documentation from a URL (it can be an HTML or a README) and adds it to a vector database.
    The variables of 'domain' and 'topic' allows to better separate the topics and gives better context to later.
    """,
)
async def ingest_document(
    ingest: IngestRequest,
    serv: RAGService = Depends(get_rag_service),
):
    await serv.ingest_document(
        url=ingest.url, source=ingest.url, domain=ingest.domain, topic=ingest.topic
    )

    return {"status": "ingested", "url": ingest.url}


@router.post(
    "/retrieve",
    description="""
    You can try to get context directly from the vector database.
    It is filtered by 'domain' and 'topic' in the database to return data.
    It is necessary to complete correctly.
    """,
)
def retrieve_search(
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
):
    query_result = serv.query(text=query.text, domain=query.domain, topic=query.topic)

    return {"status": "query", "Points": query_result}


@router.post(
    "/ask",
    description="""
    Ask to LLM about documentation previously charged and get a response with context
    """,
)
def ask(
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
) -> QueryResponse:
    return serv.ask(query.text, query.domain, query.topic)


@router.post("/ask-stream")
async def ask_stream(
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
):
    return StreamingResponse(
        serv.chat_stream(query.text, query.domain, query.topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
