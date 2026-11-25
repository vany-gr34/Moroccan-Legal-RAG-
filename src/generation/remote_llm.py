"""Remote LLM client - calls Colab GPU service."""

import os
import time
import logging
from typing import Optional
import requests
from .base import BaseLLM, GenerationResult

logger = logging.getLogger(__name__)


class RemoteLLM(BaseLLM):
    """Calls a remote LLM service (Colab GPU via Cloudflare Tunnel)."""

    def __init__(self, service_url: str = None, timeout: Optional[int] = None):
        self._service_url = (service_url or os.getenv(
            "LLM_SERVICE_URL", "")).rstrip("/")
        if not self._service_url:
            raise ValueError(
                "LLM_SERVICE_URL not set. Set it in .env or pass service_url.")
        self._timeout = timeout
        self._healthy = False
        self._model_name = "unavailable"
        self._check_health()

    def _check_health(self):
        """Check if the LLM service is reachable. Logs a warning on failure but does not raise."""
        try:
            resp = requests.get(f"{self._service_url}/health", timeout=10)
            resp.raise_for_status()
            health = resp.json()
            self._healthy = True
            self._model_name = health.get("model", "unknown")
            logger.info(f"✓ LLM service connected: {self._model_name} "
                        f"on {health.get('gpu_name', 'unknown')}")
        except requests.exceptions.RequestException as e:
            self._healthy = False
            logger.warning(
                f"⚠ LLM service unreachable at {self._service_url}: {e}")

    @property
    def name(self) -> str:
        return f"Remote LLM ({self._service_url})"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        top_p: float = 0.9,
    ) -> GenerationResult:
        start = time.time()

        # Retry health check if previously unhealthy — the service may have
        # started after this client was initialised.
        if not self._healthy:
            self._check_health()

        if not self._healthy:
            elapsed = time.time() - start
            return GenerationResult(
                response="",
                tokens_generated=0,
                generation_time_ms=round(elapsed * 1000, 2),
                model_name="unavailable",
            )

        try:
            resp = requests.post(
                f"{self._service_url}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            elapsed = time.time() - start

            return GenerationResult(
                response=data["response"],
                tokens_generated=data.get("tokens_generated", 0),
                generation_time_ms=data.get(
                    "time_ms", round(elapsed * 1000, 2)),
                model_name=self._model_name,
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"LLM generation failed: {e}")
            elapsed = time.time() - start
            return GenerationResult(
                response="",
                tokens_generated=0,
                generation_time_ms=round(elapsed * 1000, 2),
                model_name="unavailable",
            )
