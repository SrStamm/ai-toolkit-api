from fastapi import FastAPI
from app.features.extraction.router import router as extraction_router

app = FastAPI()

app.include_router(extraction_router)
