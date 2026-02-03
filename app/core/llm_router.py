# Retry Orchestra and circuit breaker

import os
import time
import structlog

from .llm_providers.mistral_provider import MistralProvider
from .llm_providers.ollama_provider import OllamaProvider
from .settings import BaseLLMProvider, LLMConfig


class LLMRouter:
    def __init__(
        self,
        primary: BaseLLMProvider,
        fallback: BaseLLMProvider,
        failure_threshold: int = 3,
        open_timeout: int = (60),
    ):
        self.primary = primary
        self.fallback = fallback

        self.failure_threshold = failure_threshold
        self.open_timeout = open_timeout

        self.failure_count = 0
        self.state = "CLOSED"
        self.opened_at = None

        self.logger = structlog.get_logger()

    def chat(self, prompt: str):
        now = time.time()

        # if state OPEN, check timeout
        # Else, fallback
        if self.state == "OPEN":
            if now - self.opened_at < self.open_timeout:
                self.state = "HALF-OPEN"
                self.logger.info("circuit_half_open")
            else:
                self.logger.info("llm_fallback_used", state=self.state, reason="OPEN")
                return self.fallback.chat(prompt)

        # If state HALF-OPEN or CLOSED, try primary
        try:
            response = self.primary.chat(prompt)

            if self.state == "HALF-OPEN":
                self.logger.info(
                    "circuit_closed",
                    previous_state="HALF-OPEN",
                    failure_count=self.failure_count,
                )

                self.state = "CLOSED"
                self.failure_count = 0

            return response
        except Exception:
            self.failure_count += 1

            # Set state to OPEN if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.opened_at = time.time()
                self.logger.warning(
                    "circuit_opened",
                    failure_count=self.failure_count,
                    timeout=self.open_timeout,
                )

            self.logger.info(
                "llm_fallback_used", state=self.state, reason="threshold reached"
            )
            return self.fallback.chat(prompt)

    def chat_stream(self, prompt: str):
        now = time.time()

        if self.state == "OPEN":
            if now - self.opened_at < self.open_timeout:
                self.state = "HALF-OPEN"
                self.logger.info("circuit_half_open")
            else:
                self.logger.info(
                    "llm_fallback_used", state=self.state, reason="active timeout"
                )
                return self.fallback.chat_stream(prompt)

        try:
            response = self.primary.chat_stream(prompt)

            if self.state == "HALF-OPEN":
                self.logger.info(
                    "circuit_closed",
                    previous_state="HALF-OPEN",
                    failure_count=self.failure_count,
                )

                self.state = "CLOSED"
                self.failure_count = 0

            return response
        except Exception:
            self.failure_count += 1

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.opened_at = time.time()

                self.logger.warning(
                    "circuit_opened",
                    failure_count=self.failure_count,
                    timeout=self.open_timeout,
                )

            self.logger.info(
                "llm_fallback_used", state=self.state, reason="threshold reached"
            )
            return self.fallback.chat_stream(prompt)


def get_llm_router() -> LLMRouter:
    API_KEY = os.getenv("MISTRAL_API_KEY")

    if not API_KEY:
        raise ValueError("API_KEY no configurada")

    config = LLMConfig(api_key=API_KEY)

    primary = MistralProvider(config)
    fallback = OllamaProvider()
    return LLMRouter(primary, fallback)
