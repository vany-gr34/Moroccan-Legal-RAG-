"""OpenAI-compatible LLM client.

Uses the `openai` Python SDK to call any OpenAI-compatible API
(DeepSeek, OpenAI, Together AI, etc.) while implementing the
`BaseLLM` interface for seamless integration with the existing
ask endpoint and RAG pipeline.

Usage in .env:
    LLM_BACKEND=openai
    OPENAI_API_KEY=sk-...
    OPENAI_BASE_URL=https://api.deepseek.com
    OPENAI_MODEL=deepseek-chat
"""

import os
import time
import logging
from typing import Optional

from ..generation.base import BaseLLM, GenerationResult

logger = logging.getLogger(__name__)

# Default system prompt for legal RAG
DEFAULT_SYSTEM_PROMPT = (
    "أنت مساعد قانوني مغربي متخصص. تجيب على الأسئلة القانونية بناء على "
    "النصوص القانونية المقدمة فقط. لا تخترع معلومات غير موجودة في النصوص. "
    "تذكر أرقام المواد التي استندت إليها في إجابتك. "
    "إذا لم تكن الإجابة موجودة في النصوص المقدمة فقل ذلك بوضوح.\n\n"
    "📋 **تعليمات التنسيق**\n\n"
    "قدم إجابتك بتنسيق Markdown منظم وفق الهيكل التالي:\n\n"
    "### 1. ملخص الإجابة\n"
    "إجابة مختصرة مباشرة (جملة أو جملتين)\n\n"
    "### 2. التحليل القانوني\n"
    "- شرح كيف تجيب كل مادة قانونية مسترجعة على السؤال\n"
    "- اربط بين السؤال والنصوص القانونية بشكل واضح\n"
    "- استشهد بأرقام المواد أثناء الشرح\n\n"
    "### 3. الخلاصة\n"
    "استنتاج نهائي مبني على التحليل أعلاه\n\n"
    "### 4. المواد القانونية المستند إليها\n"
    "- **المادة [الرقم]** من **[اسم القانون]** – [سبب الاستناد إليها]\n\n"
    "> ⚖️ *هذا تحليل آلي بناء على النصوص المسترجعة*"
)


class OpenAILLM(BaseLLM):
    """LLM client using the OpenAI Python SDK.

    Compatible with any OpenAI-compatible API provider:
      - DeepSeek (api.deepseek.com)
      - OpenAI (api.openai.com)
      - Together AI, Groq, etc.

    Configure via environment variables:
        LLM_BACKEND=openai
        OPENAI_API_KEY    - API key (required)
        OPENAI_BASE_URL   - API base URL (default: https://api.deepseek.com)
        OPENAI_MODEL      - Model name (default: deepseek-chat)
        OPENAI_MAX_TOKENS - Max generation tokens (default: 4096)
        OPENAI_TIMEOUT    - Request timeout in seconds (default: 120)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL", "")
            or "https://api.deepseek.com"
        )
        self._model = model or os.getenv("OPENAI_MODEL", "deepseek-chat")
        self._max_tokens = int(
            os.getenv("OPENAI_MAX_TOKENS", str(max_tokens)))
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self._client = None

        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY not set. Provide api_key or set "
                "the OPENAI_API_KEY environment variable."
            )

    def _ensure_client(self):
        """Lazy-init the OpenAI client."""
        if self._client is not None:
            return

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        # Disable timeout entirely — the API call can take a long time
        # for long legal answers. The request-level timeout in the
        # FastAPI / uvicorn layer will still apply if set.
        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=None,
        )
        logger.info(
            f"✓ OpenAI client ready: model={self._model}, base_url={self._base_url}")

    @property
    def name(self) -> str:
        return f"OpenAI ({self._model})"

    def generate(
        self,
        prompt: str,
        # 0 means "use instance default (OPENAI_MAX_TOKENS)"
        max_tokens: int = 0,
        temperature: float = 0.3,
        top_p: float = 0.9,
    ) -> GenerationResult:
        """Send a prompt to the OpenAI-compatible API and return the response.

        Args:
            prompt: The full prompt text (already includes context + question).
            max_tokens: Max tokens (0 = use OPENAI_MAX_TOKENS env / instance default).
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.

        Returns:
            GenerationResult with response text and metadata.
        """
        start = time.time()
        self._ensure_client()

        resolved_max_tokens = max_tokens if max_tokens else self._max_tokens

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=resolved_max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False,
            )

            elapsed = time.time() - start

            choice = response.choices[0]
            generated_text = choice.message.content or ""

            usage = response.usage
            tokens_generated = usage.completion_tokens if usage else len(
                generated_text.split())

            return GenerationResult(
                response=generated_text.strip(),
                tokens_generated=tokens_generated,
                generation_time_ms=round(elapsed * 1000, 2),
                model_name=self._model,
            )

        except Exception as e:
            logger.error(f"OpenAI LLM generation failed: {e}")
            elapsed = time.time() - start
            return GenerationResult(
                response="",
                tokens_generated=0,
                generation_time_ms=round(elapsed * 1000, 2),
                model_name="unavailable",
            )
