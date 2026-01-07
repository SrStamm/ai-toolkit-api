from fastapi import APIRouter, Depends
from app.features.extraction.service import ExtractionService, get_extraction_service

router = APIRouter(prefix="/extraction")


@router.get("/person")
def extract_person_info(
    raw_text: str, serv: ExtractionService = Depends(get_extraction_service)
):
    return serv.extract_person_info(raw_text)
