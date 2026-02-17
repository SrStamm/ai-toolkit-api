from ....application.llm.client import LLMClient
from ..prompts import (
    EXTRACTION_FILE_PDF_PROMPT,
    EXTRACTION_FILE_PROMPT,
)
from ..schema import InvoiceList, InvoiceSchema


class InvoiceExtractor:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def from_csv_text(self, text: str):
        prompt = EXTRACTION_FILE_PROMPT.format(text=text)
        return self.llm.generate_structured_output(prompt, InvoiceList)

    def from_pdf_text(self, text: str):
        prompt = EXTRACTION_FILE_PDF_PROMPT.format(text=text)
        return self.llm.generate_structured_output(prompt, output_schema=InvoiceSchema)
