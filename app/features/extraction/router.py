from fastapi import APIRouter, Depends, UploadFile
from .service import ExtractionService, get_extraction_service

router = APIRouter(prefix="/extraction", tags=["Extraction"])


@router.get("/person")
def extract_person_info(
    raw_text: str, serv: ExtractionService = Depends(get_extraction_service)
):
    return serv.extract_data_for_person(raw_text)


@router.post("/extract-invoice")
async def extract_invoice(
    file: UploadFile, serv: ExtractionService = Depends(get_extraction_service)
):
    return await serv.extract_data_from_file(file)
