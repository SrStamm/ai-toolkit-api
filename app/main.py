from fastapi import FastAPI
from app.features.extraction.router import router as extraction_router
from app.features.rag.router import router as rag_router

app = FastAPI()

app.include_router(extraction_router)
app.include_router(rag_router)
