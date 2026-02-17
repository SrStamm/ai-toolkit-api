# Provider for LLM

from typing import AsyncIterator, Optional

from .llm_router import LLMRouter, get_llm_router
from .models import LLMResponse
from .custom_logging import time_response
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self, router: LLMRouter):
        self.router = router

    @time_response
    def generate_content(self, prompt: str) -> LLMResponse[str]:
        return self.router.chat(prompt)

    @time_response
    def generate_structured_output(
        self, prompt: str, output_schema: type[BaseModel]
    ) -> LLMResponse[BaseModel]:
        structured_prompt = f"{prompt}\n Output como JSON válido, únicamente devuelve el objeto JSON, conforme a este schema: {output_schema.model_json_schema()}"

        response = self.router.chat(structured_prompt)

        try:
            parsed_content = output_schema.model_validate_json(response)

            return LLMResponse(
                content=parsed_content,
                usage=response.usage,
                cost=response.cost,
                model=response.model,
                provider=response.provider,
            )

        except ValidationError:
            error_prompt = f"{structured_prompt}\nPrevious output invalid. Corrige: {response.content}"
            return self.generate_structured_output(error_prompt, output_schema)

    async def generate_content_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
        async for chunk, final_response in self.router.chat_stream(prompt):
            yield (chunk, final_response)


def get_llm_client():
    router: LLMRouter = get_llm_router()
    return LLMClient(router)
