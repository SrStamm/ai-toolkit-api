import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import structlog

from .prompt import PROMPT_TEMPLATE
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
    async def generate():
        # 1. Recuperar contexto
        query_result = serv.query(query.text, query.domain, query.topic)

        if not query_result:
            yield f"data: {json.dumps({'type': 'error', 'content': 'No results found'})}\n\n"
            return

        rerank_result = serv.vector_store.rerank(query.text, query_result)

        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(rerank_result)
        )

        prompt = PROMPT_TEMPLATE.format(context=context, question=query.text)

        # 2. LLM Stream response
        final_response = None
        async for chunk, response_data in serv.llm_client.generate_content_stream(
            prompt
        ):
            if response_data:
                final_response = response_data
            else:
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0)

        # 3. Costs logs
        if final_response:
            logger = structlog.get_logger()
            logger.info(
                "LLM_CALL_STREAM",
                provider=final_response.provider,
                model=final_response.model,
                prompt_tokens=final_response.usage.prompt_tokens,
                completion_tokens=final_response.usage.completion_tokens,
                total_tokens=final_response.usage.total_tokens,
                input_cost=f"${final_response.cost.input_cost:.6f}",
                output_cost=f"${final_response.cost.output_cost:.6f}",
                total_cost=f"${final_response.cost.total_cost:.6f}",
            )

        # 4. Send citations
        seen = set()
        citations = []
        for q in query_result:
            src = q.payload["source"]
            if src not in seen:
                seen.add(src)
                citations.append(
                    {"source": src, "chunk_index": q.payload["chunk_index"]}
                )

        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

        # 5. Send final metadata
        if final_response:
            yield f"data: {
                json.dumps(
                    {
                        'type': 'metadata',
                        'tokens': final_response.usage.total_tokens,
                        'cost': final_response.cost.total_cost,
                        'model': final_response.model,
                        'estimated': True,
                    }
                )
            }\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
