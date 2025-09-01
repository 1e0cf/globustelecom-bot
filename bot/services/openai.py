from __future__ import annotations
import asyncio
from functools import lru_cache
from pathlib import Path
from time import perf_counter

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from loguru import logger

from bot.core.config import DIR, settings


class OpenAIClient:
    """Thin wrapper around OpenAI API for Q&A."""

    def __init__(self, api_key: str, model_name: str = "gpt-5-nano") -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name
        logger.debug("OpenAIClient initialized | model={}", model_name)

    @staticmethod
    @lru_cache(maxsize=1)
    def load_knowledge_base() -> str:
        """Load the knowledge base from a JSON file."""
        path = Path(DIR) / "knowledge_base.json"
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    async def answer(self, question: str, language_code: str) -> str:
        """Generate an answer using the selected language and FAQ context."""
        knowledge_base = self.load_knowledge_base()

        language = (language_code or "en").strip().lower()
        # Map Telegram codes to names as hint for the model
        lang_label = {
            "en": "English",
            "es": "Spanish",
            "pt": "Portuguese",
            "fr": "French",
            "de": "German",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ru": "Russian",
            "ar": "Arabic",
        }.get(language, language)

        system_prompt = (
            "You are a helpful, technically skilled support manager for the eSIM store globustele.com. "
            "Answer strictly in the user's language: {lang}. Be concise, accurate and practical. "
            "Use the provided knowledge base in json format. If a policy or price is unknown, say that it's unclear and suggest contacting support."
        ).format(lang=lang_label)

        # Prepare messages for OpenAI
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
        ]

        if knowledge_base:
            messages.append({"role": "user", "content": f"Knowledge base content:\n{knowledge_base}"})

        messages.append({"role": "user", "content": f"User question (reply in {lang_label}):\n{question}"})

        # Retry strategy for transient issues
        attempts = [0.0, 0.8, 1.6]
        last_error: Exception | None = None
        for attempt, delay in enumerate(attempts, start=1):
            try:
                start = perf_counter()
                logger.info(
                    "OpenAI request \u2192 sending | attempt={} | lang={} | q_len={} | knowledge_base_len={}",
                    attempt,
                    lang_label,
                    len(question or ""),
                    len(knowledge_base or ""),
                )

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    # max_completion_tokens=1024,
                )

                elapsed_ms = int((perf_counter() - start) * 1000)

                finish_reason = response.choices[0].finish_reason if response.choices else None

                text: str = response.choices[0].message.content or "" if response.choices else ""
                text = text.strip()

                logger.info(
                    "OpenAI response \u2190 received | ms={} | text_len={} | finish_reason={}",
                    elapsed_ms,
                    len(text),
                    finish_reason,
                )
                return text or ""
            except Exception as e:
                last_error = e
                msg = str(e)
                is_5xx = "500" in msg or "InternalServerError" in msg
                is_resource = "RateLimitError" in msg or "quota" in msg.lower()
                logger.error("OpenAI request failed | attempt={} | error={}", attempt, msg)

                if attempt < len(attempts) and (is_5xx or is_resource):
                    await asyncio.sleep(delay)
                    # On retry, try slimmer prompt without FAQ for robustness
                    if attempt == 2 and knowledge_base:
                        logger.debug("Retrying without Knowledge base context to reduce payload")
                        messages = [msg for msg in messages if "Knowledge base content" not in (msg.get("content") or "")]
                    continue
                break

        logger.exception("OpenAI request failed after retries: {}", last_error)
        return ""


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    """Get a singleton instance of the OpenAI client."""
    api_key = settings.OPENAI_API_KEY or ""
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAIClient(api_key=api_key)
