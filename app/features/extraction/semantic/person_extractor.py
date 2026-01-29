from ....core.llm_client import LLMClient
from ..prompts import EXTRACTION_PROMPT
from ..schema import PersonSchema


class PersonExtractor:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def extract_person_info(self, raw_text: str):
        prompt = EXTRACTION_PROMPT.format(text=raw_text)
        return self.llm.generate_structured_output(prompt, PersonSchema)
