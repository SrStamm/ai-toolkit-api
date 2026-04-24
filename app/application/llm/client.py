# Provider for LLM

from collections.abc import AsyncIterator
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from ...infrastructure.logging import time_response
from ...domain.models import LLMResponse
from ...domain.exceptions import StructuredOutputError
from ...domain.services.router import LLMRouter, get_llm_router
from ...domain.providers.base import Message

load_dotenv()

MAX_STRUCTURED_OUTPUT_RETRIES = 2


class LLMClient:
    def __init__(self, router: LLMRouter):
        self.router = router

    @time_response
    def generate_content(self, prompt: str) -> LLMResponse[str]:
        return self.router.chat(prompt)

    @time_response
    def generate_content_with_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Generate content using message history and optional system prompt.

        Args:
            messages: List of messages with role and content.
            system_prompt: Optional system prompt to prepend.
        """
        return self.router.chat_with_messages(messages, system_prompt)

    @time_response
    def generate_structured_output(
        self,
        prompt: str,
        output_schema: type[BaseModel],
        _retries: int = 0,
    ) -> LLMResponse[BaseModel]:
        if _retries >= MAX_STRUCTURED_OUTPUT_RETRIES:
            raise StructuredOutputError(
                f"Failed to parse structured output after {MAX_STRUCTURED_OUTPUT_RETRIES} attempts"
            )

        structured_prompt = (
            f"{prompt}\n Output como JSON válido, únicamente devuelve el objeto JSON, "
            f"conforme a este schema: {output_schema.model_json_schema()}"
        )

        response = self.router.chat(structured_prompt)

        try:
            parsed_content = output_schema.model_validate_json(response.content)

            return LLMResponse(
                content=parsed_content,
                usage=response.usage,
                cost=response.cost,
                model=response.model,
                provider=response.provider,
            )

        except ValidationError:
            error_prompt = (
                f"{structured_prompt}\nPrevious output invalid. "
                f"Corrige el formato JSON. Respuesta inválida: {response.content}"
            )
            return self.generate_structured_output(
                error_prompt, output_schema, _retries=_retries + 1
            )

    async def generate_content_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, LLMResponse[str] | None]]:
        async for chunk, final_response in self.router.chat_stream(prompt):
            yield (chunk, final_response)


def get_llm_client():
    router: LLMRouter = get_llm_router()
    return LLMClient(router)
