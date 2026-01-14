from fastapi import APIRouter, Depends, UploadFile
from app.features.extraction.service import ExtractionService, get_extraction_service

router = APIRouter(prefix="/extraction")


@router.get("/person")
def extract_person_info(
    raw_text: str, serv: ExtractionService = Depends(get_extraction_service)
):
    return serv.extract_person_info(raw_text)


@router.post("/extract-csv")
async def extract_csv_info(
    file: UploadFile, serv: ExtractionService = Depends(get_extraction_service)
):
    return await serv.extract_data_from_csv(file)


@router.post("/extract-pdf")
async def extract_pdf_info(
    file: UploadFile, serv: ExtractionService = Depends(get_extraction_service)
):
    return await serv.extract_data_from_pdf(file)


@router.post("/extract-invoice")
async def extract_invoice(
    file: UploadFile, serv: ExtractionService = Depends(get_extraction_service)
):
    return await serv.extract_data_from_file(file)
