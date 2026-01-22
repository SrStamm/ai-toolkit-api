from fastapi import Depends, HTTPException, UploadFile
from app.core.llm_client import LLMClient, get_llm_client
from app.features.extraction.semantic.invoice_extractor import InvoiceExtractor
from app.features.extraction.semantic.person_extractor import PersonExtractor
from app.features.extraction.source.csv_source import CSVSource
from app.features.extraction.source.pdf_source import PDFSource


class ExtractionService:
    def __init__(self, llm: LLMClient) -> None:
        self.invoice_extractor = InvoiceExtractor(llm)
        self.person_extractor = PersonExtractor(llm)
        self.llm = llm

    def extract_data_for_person(self, text: str):
        return self.person_extractor.extract_person_info(text)

    async def extract_data_from_file(self, file: UploadFile):
        type_file = file.filename.split(".")[-1]

        if type_file == "csv":
            content = await CSVSource().extract_data_from_csv(file)
            return self.invoice_extractor.from_csv_text(content)

        elif type_file == "pdf":
            text = await PDFSource().extract_data_from_pdf(file)
            return self.invoice_extractor.from_pdf_text(text)

        else:
            return {"error": "Tipo de archivo no soportado"}


def get_extraction_service(
    llm_client: LLMClient = Depends(get_llm_client),
) -> ExtractionService:
    return ExtractionService(llm_client)
