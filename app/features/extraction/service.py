from io import BytesIO, StringIO
import chardet
import pdfplumber
from fastapi import Depends, HTTPException
from app.core.llm_client import LLMClient, get_llm_client
from .prompts import (
    EXTRACTION_FILE_PDF_PROMPT,
    EXTRACTION_FILE_PROMPT,
    EXTRACTION_PROMPT,
)
from .schema import InvoiceList, InvoiceSchema, PersonSchema
import pandas as pd


class ExtractionService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def extract_person_info(self, raw_text: str):
        full_prompt = EXTRACTION_PROMPT.format(text=raw_text)
        return self.llm_client.generate_structured_output(
            full_prompt, output_schema=PersonSchema
        )

    async def extract_data_from_csv(self, file) -> str:
        # Read file
        file_content = await file.read()

        # Detect encoding automatically
        detector = chardet.universaldetector.UniversalDetector()
        detector.reset()
        detector.feed(file_content)
        detector.close()
        detected = detector.result
        encoding = detected["encoding"] or "iso-8859-1"

        # Decode file
        try:
            text = file_content.decode(encoding)
        except UnicodeDecodeError:
            text = file_content.decode("utf-8", errors="replace")

        # Convert file to dataframe
        try:
            df = pd.read_csv(StringIO(text), sep=";", on_bad_lines="skip")
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error procesando CSV: {str(e)}"
            )

        if df.empty:
            raise ValueError("El CSV está vacío o no se pudo parsear")

        return df.head(5).to_string(index=False)

    async def extract_data_from_pdf(self, file):
        # Read file
        file_content = await file.read()

        # Open file
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            full_text = "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )
            return full_text

    async def extract_data_from_file(self, file):
        type_file = file.filename.lower().split(".")[-1]

        if type_file == "csv":
            content = await self.extract_data_from_csv(file)
            print("content: ", content)
            full_prompt = EXTRACTION_FILE_PROMPT.format(text=content)

            response = self.llm_client.generate_structured_output(
                full_prompt, output_schema=InvoiceList
            )

            # Validate response
            return response

        elif type_file == "pdf":
            content = await self.extract_data_from_pdf(file)
            full_prompt = EXTRACTION_FILE_PDF_PROMPT.format(text=content)

            return self.llm_client.generate_structured_output(
                full_prompt, output_schema=InvoiceSchema
            )

        else:
            return {"error": "Tipo de archivo no soportado"}


def get_extraction_service(
    llm_client: LLMClient = Depends(get_llm_client),
) -> ExtractionService:
    return ExtractionService(llm_client)
