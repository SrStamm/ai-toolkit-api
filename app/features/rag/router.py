import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import structlog

from features.extraction.exceptions import EmptySourceContentError
from features.rag.exceptions import ChunkingError, EmbeddingError
from .schemas import IngestRequest, QueryRequest, QueryResponse
from .service import RAGService, get_rag_service

router = APIRouter(prefix="/rag", tags=["RAG"])

logger = structlog.getLogger()


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
    "/ingest-stream",
    description="""
    It ingests documentation from a URL (it can be an HTML or a README) and adds it to a vector database.
    The variables of 'domain' and 'topic' allows to better separate the topics and gives better context to later.
    """,
)
async def ingest_document_stream(
    ingest: IngestRequest,
    serv: RAGService = Depends(get_rag_service),
):
    async def generate():
        try:
            async for event in serv.ingest_document_stream(
                url=ingest.url,
                source=ingest.url,
                domain=ingest.domain,
                topic=ingest.topic,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except EmptySourceContentError:
            yield {
                "type": "error",
                "message": "Document is empty after cleaning",
                "recoverable": False,
            }
        except ChunkingError:
            yield {
                "type": "error",
                "message": "Failed to split document",
                "recoverable": False,
            }
        except EmbeddingError as e:
            yield {
                "type": "error",
                "message": f"Embedding failed: {str(e)}",
                "recoverable": True,
            }
        except asyncio.TimeoutError:
            yield {
                "type": "error",
                "message": "Processing timed out, try a smaller document",
                "recoverable": False,
            }

    return StreamingResponse(generate(), media_type="text/event-stream")


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
