from fastapi import Depends
from app.core.llm_client import LLMClient, get_llm_client
from .prompts import EXTRACTION_PROMPT
from .schema import PersonSchema


class ExtractionService:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def extract_person_info(self, raw_text: str):
        full_prompt = EXTRACTION_PROMPT.format(text=raw_text)
        return self.llm_client.generate_structured_output(
            full_prompt, output_schema=PersonSchema
        )


def get_extraction_service(
    llm_client: LLMClient = Depends(get_llm_client),
) -> ExtractionService:
    return ExtractionService(llm_client)
