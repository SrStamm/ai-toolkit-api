# Retry Orchestra and circuit breaker

import os
import time
import structlog
import threading

from .llm_providers.mistral_provider import MistralProvider
from .llm_providers.ollama_provider import OllamaProvider
from .settings import BaseLLMProvider, LLMConfig
from .metrics import (
    llm_requests_total,
    llm_request_duration_seconds,
    llm_fallback_total,
    circuit_state_changes_total,
)


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

        self._lock = threading.Lock()

        self.logger = structlog.get_logger()

    def _on_failure(self):
        with self._lock:
            self.failure_count += 1

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = time.time()
            self.logger.warning(
                    "circuit_opened",
                    failure_count=self.failure_count,
                    timeout=self.open_timeout,
            )

    def chat(self, prompt: str):
        now = time.time()
        provider_name = self.primary.name
        model_name = self.primary.model

        if self.state == "OPEN":
            if now - self.opened_at >= self.open_timeout:
                self.state = "HALF-OPEN"
                circuit_state_changes_total.labels("HALF-OPEN").inc()
                self.logger.info("circuit_half_open")
            else:
                llm_fallback_total.labels(
                    provider_name,
                    self.fallback.name
                ).inc()

                llm_requests_total.labels(
                    self.fallback.name,
                    self.fallback.model,
                    "fallback"
                ).inc()

                self.logger.info("llm_fallback_used", state=self.state, reason="OPEN")
                return self.fallback.chat(prompt)

        start = time.perf_counter()

        try:
            response = self.primary.chat(prompt)

            duration = time.perf_counter() - start

            llm_request_duration_seconds.labels(
                provider_name,
                model_name
            ).observe(duration)

            llm_requests_total.labels(
                provider_name,
                model_name,
                "success"
            ).inc()

            with self._lock:
                if self.state == "HALF-OPEN":
                    self.logger.info(
                        "circuit_closed",
                        previous_state="HALF-OPEN",
                        failure_count=self.failure_count,
                    )

                    self.state = "CLOSED"
                    self.failure_count = 0
                    circuit_state_changes_total.labels("CLOSED").inc()

            return response

        except Exception:
            duration = time.perf_counter() - start
            llm_request_duration_seconds.labels(
                provider_name,
                model_name
            ).observe(duration)

            llm_requests_total.labels(
                provider_name,
                model_name,
                "error"
            ).inc()

            self._on_failure()

            self.logger.info(
                "llm_fallback_used", state=self.state, reason="threshold reached"
            )

            llm_fallback_total.labels(
                provider_name,
                self.fallback.name,
            ).inc()

            start_fb = time.perf_counter()
            response = self.fallback.chat(prompt)
            duration_fb = time.perf_counter() - start_fb

            llm_request_duration_seconds.labels(
                self.fallback.name,
                self.fallback.model
            ).observe(duration_fb)

            llm_requests_total.labels(
                self.fallback.name,
                self.fallback.model,
                "fallback"
            ).inc()

            return response

    def chat_stream(self, prompt: str):
        async def _stream():
            provider_name = self.primary.name
            model_name = self.primary.model

            start = time.perf_counter()

            try:
                async for chunk in self.primary.chat_stream(prompt):
                    yield chunk

                duration = time.perf_counter() - start

                llm_request_duration_seconds.labels(
                    provider_name,
                    model_name
                ).observe(duration)

                llm_requests_total.labels(
                    provider_name,
                    model_name,
                    "success"
                ).inc()

                with self._lock:
                    if self.state == "HALF-OPEN":
                        self.state = "CLOSED"
                        self.failure_count = 0
                        circuit_state_changes_total.labels("CLOSED").inc()

            except Exception:
                self._on_failure()

                llm_requests_total.labels(
                    provider_name,
                    model_name,
                    "error"
                ).inc()

                llm_fallback_total.labels(
                    provider_name,
                    self.fallback.name
                ).inc()


                async for chunk in self.fallback.chat_stream(prompt):
                    yield chunk

        return _stream()



def get_llm_router() -> LLMRouter:
    API_KEY = os.getenv("MISTRAL_API_KEY")
    OLLAMA_MODEL= os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    OLLAMA_URL= os.getenv("OLLAMA_URL", "http://localhost:11434")

    if not API_KEY:
        raise ValueError("API_KEY no configurada")

    config = LLMConfig(api_key=API_KEY)
    config_ollama = LLMConfig(api_key="", model=OLLAMA_MODEL, url=OLLAMA_URL)

    return LLMRouter(
        primary= MistralProvider(config),
        fallback=OllamaProvider(config_ollama)
    )
