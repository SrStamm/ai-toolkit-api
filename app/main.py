from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.features.extraction.router import router as extraction_router
from app.features.rag.rag_client import get_rag_client, RAGClient
from app.features.rag.router import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando APP")
    print("Verificando colección")
    rag_client: RAGClient = get_rag_client()
    rag_client.create_collection()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(extraction_router)
app.include_router(rag_router)
