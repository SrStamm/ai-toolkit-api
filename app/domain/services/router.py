# Retry Orchestra and circuit breaker

import os
import time
import structlog
import threading

from ..providers.factory_provider import LLMFactory
from ..providers.base import BaseLLMProvider
from ...core.settings import LLMConfig
from ...infrastructure.metrics import (
    llm_requests_total,
    llm_request_duration_seconds,
    llm_fallback_total,
    circuit_state_changes_total,
    llm_circuit_state,
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

        # Initialize gauge to CLOSED (0)
        llm_circuit_state.set(0)

    def _update_circuit_gauge(self, state: str):
        """Update the circuit breaker gauge: 0=CLOSED, 1=HALF-OPEN, 2=OPEN"""
        state_map = {"CLOSED": 0, "HALF-OPEN": 1, "OPEN": 2}
        llm_circuit_state.set(state_map.get(state, 0))

    def _on_failure(self):
        with self._lock:
            self.failure_count += 1

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = time.time()
            self._update_circuit_gauge("OPEN")
            circuit_state_changes_total.labels("OPEN").inc()
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
                self._update_circuit_gauge("HALF-OPEN")
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
                    self._update_circuit_gauge("CLOSED")
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
                        self._update_circuit_gauge("CLOSED")
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
    config_primary = LLMConfig(
        provider="mistral",
        api_key=os.getenv("MISTRAL_API_KEY")
    )

    config_fallback = LLMConfig(
        provider="ollama",
        api_key="",
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        url=os.getenv("OLLAMA_URL", "http://localhost:11434")
    )

    primary = LLMFactory.create_provider(config_primary)
    fallback= LLMFactory.create_provider(config_fallback)

    return LLMRouter(
        primary=primary,
        fallback=fallback
    )
