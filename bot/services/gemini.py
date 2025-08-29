from __future__ import annotations
import asyncio
from functools import lru_cache
from pathlib import Path
from time import perf_counter

import google.generativeai as genai
from loguru import logger

from bot.core.config import DIR, settings


class GeminiClient:
    """Thin wrapper around Google Gemini 2.5 Flash-Lite for Q&A."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-lite") -> None:
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.9,
                "max_output_tokens": 1024,
            },
        )
        logger.debug("GeminiClient initialized | model={}", model_name)

    @staticmethod
    @lru_cache(maxsize=1)
    def load_knowledge_base() -> str:
        path = Path(DIR) / "knowledge_base.json"
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    async def answer(self, question: str, language_code: str) -> str:
        """Generate an answer using the selected language and FAQ context."""
        knowledge_base = self.load_knowledge_base()
        # Constrain FAQ size to reduce server-side errors
        # MAX_FAQ_CHARS = 8000
        # if knowledge_base and len(knowledge_base) > MAX_FAQ_CHARS:
        #     logger.debug("Truncating knowledge base from {} to {} chars", len(knowledge_base), MAX_FAQ_CHARS)
        #     knowledge_base = knowledge_base[:MAX_FAQ_CHARS]

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

        # Gemini expects roles to be either "user" or "model".
        # We inject the instruction as a user message to avoid invalid role errors.
        content = [
            {"role": "user", "parts": [system_prompt]},
        ]

        if knowledge_base:
            content.append({"role": "user", "parts": [f"Knowledge base content:\n{knowledge_base}"]})

        content.append({"role": "user", "parts": [f"User question (reply in {lang_label}):\n{question}"]})

        # Retry strategy for transient 5xx issues
        attempts = [0.0, 0.8, 1.6]
        last_error: Exception | None = None
        for attempt, delay in enumerate(attempts, start=1):
            try:
                start = perf_counter()
                logger.info(
                    "Gemini request → sending | attempt={} | lang={} | q_len={} | knowledge_base_len={}",
                    attempt,
                    lang_label,
                    len(question or ""),
                    len(knowledge_base or ""),
                )
                response = await self.model.generate_content_async(content)
                elapsed_ms = int((perf_counter() - start) * 1000)

                finish_reasons = []
                safety_blocks = []
                try:
                    candidates = getattr(response, "candidates", None) or []
                    for cand in candidates:
                        fr = getattr(cand, "finish_reason", None)
                        if fr:
                            finish_reasons.append(str(fr))
                        ratings = getattr(cand, "safety_ratings", None) or []
                        for r in ratings:
                            cat = getattr(r, "category", None)
                            blk = getattr(r, "blocked", None)
                            if blk:
                                safety_blocks.append(str(cat))
                    pf = getattr(response, "prompt_feedback", None)
                    if pf and getattr(pf, "block_reason", None):
                        safety_blocks.append(str(getattr(pf, "block_reason")))
                except Exception as _e:
                    logger.debug("Gemini response summarize failed: {}", _e)

                text: str = (getattr(response, "text", "") or "").strip()
                logger.info(
                    "Gemini response ← received | ms={} | text_len={} | finish_reasons={} | safety_blocks={}",
                    elapsed_ms,
                    len(text),
                    finish_reasons or None,
                    safety_blocks or None,
                )
                return text or ""
            except Exception as e:
                last_error = e
                msg = str(e)
                is_5xx = "InternalServerError" in msg or msg.startswith("500 ")
                is_resource = "ResourceExhausted" in msg or "quota" in msg.lower()
                logger.error("Gemini request failed | attempt={} | error={}", attempt, msg)

                if attempt < len(attempts) and (is_5xx or is_resource):
                    await asyncio.sleep(delay)
                    # On retry, try slimmer prompt without FAQ for robustness
                    if attempt == 2 and knowledge_base:
                        logger.debug("Retrying without Knowledge base context to reduce payload")
                        content = [c for c in content if "Knowledge base content" not in (c.get("parts", [""])[0] or "")]
                    continue
                break

        logger.exception("Gemini request failed after retries: {}", last_error)
        return ""


@lru_cache(maxsize=1)
def get_gemini_client() -> GeminiClient:
    api_key = settings.GEMINI_API_KEY or ""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return GeminiClient(api_key=api_key)


