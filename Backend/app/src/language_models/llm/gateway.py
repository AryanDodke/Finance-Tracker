"""
LLM Gateway: ordered fallback across Claude → Gemini → Groq → OpenRouter.
No feature calls providers directly – everything goes through Gateway.run().
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

# ─── Exceptions ──────────────────────────────────────────────────────────────

class RateLimitError(Exception):
    pass


class InvalidJSONError(Exception):
    pass


class AllProvidersFailed(Exception):
    pass


# ─── Base Protocol ───────────────────────────────────────────────────────────

class LLMClient(ABC):
    name: str = "base"

    @abstractmethod
    def complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict:
        """Call LLM and return validated JSON matching schema."""
        ...

    def is_available(self) -> bool:
        return True


# ─── Redactor ────────────────────────────────────────────────────────────────

_ACCOUNT_RE = re.compile(r"\b\d{9,18}\b")
_PHONE_RE = re.compile(r"\b[6-9]\d{9}\b")
_UPI_ID_RE = re.compile(r"[\w.+-]+@[\w]+")
_BALANCE_RE = re.compile(r"(?:balance|bal)[:\s]+[\d,]+(?:\.\d+)?", re.IGNORECASE)


def redact(text: str) -> str:
    """Strip account numbers, phone numbers, UPI IDs, balance mentions."""
    text = _ACCOUNT_RE.sub("[ACC]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    text = _UPI_ID_RE.sub("[UPI]", text)
    text = _BALANCE_RE.sub("balance [AMT]", text)
    return text


def redact_names(text: str, known_names: list[str]) -> str:
    """Replace known person names with [NAME]."""
    for name in known_names:
        if name and len(name) > 2:
            text = re.sub(re.escape(name), "[NAME]", text, flags=re.IGNORECASE)
    return text


# ─── Usage Tracker ───────────────────────────────────────────────────────────

class UsageTracker:
    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def record(self, provider: str, ok: bool) -> None:
        if not self._session_factory:
            return
        try:
            from datetime import date

            from app.src.models.db_models import LlmUsage
            today = date.today().isoformat()
            with self._session_factory() as s:
                usage = s.query(LlmUsage).filter_by(provider=provider, date=today).first()
                if not usage:
                    usage = LlmUsage(provider=provider, date=today, calls=0, failures=0)
                    s.add(usage)
                usage.calls += 1
                if not ok:
                    usage.failures += 1
                s.commit()
        except Exception:
            pass

    def remaining(self, provider: str) -> int | None:
        return None   # Implement rate limit tracking if needed


# ─── Claude adapter ──────────────────────────────────────────────────────────

class ClaudeClient(LLMClient):
    name = "claude"

    def __init__(self, api_key: str):
        self._key = api_key

    def is_available(self) -> bool:
        return bool(self._key)

    def complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict:
        import anthropic
        client = anthropic.Anthropic(api_key=self._key)
        try:
            msg = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=max_tokens,
                system=system + "\n\nRespond ONLY with valid JSON matching the provided schema. No markdown fences.",
                messages=[{"role": "user", "content": user}],
            )
            raw = msg.content[0].text.strip()
            return _parse_json(raw)
        except anthropic.RateLimitError:
            raise RateLimitError("Claude rate limit")
        except Exception as e:
            raise InvalidJSONError(f"Claude error: {e}")


# ─── Gemini adapter ──────────────────────────────────────────────────────────

class GeminiClient(LLMClient):
    name = "gemini"

    def __init__(self, api_key: str):
        self._key = api_key

    def is_available(self) -> bool:
        return bool(self._key)

    def complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict:
        import google.generativeai as genai
        genai.configure(api_key=self._key)
        model = genai.GenerativeModel(
            "gemini-3.8-flash",
            generation_config={"response_mime_type": "application/json"},
        )
        try:
            prompt = f"{system}\n\n{user}"
            response = model.generate_content(prompt)
            raw = response.text.strip()
            return _parse_json(raw)
        except Exception as e:
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                raise RateLimitError(f"Gemini rate limit: {e}")
            raise InvalidJSONError(f"Gemini error: {e}")


# ─── Groq adapter ────────────────────────────────────────────────────────────

class GroqClient(LLMClient):
    name = "groq"

    def __init__(self, api_key: str):
        self._key = api_key

    def is_available(self) -> bool:
        return bool(self._key)

    def complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict:
        from groq import Groq
        client = Groq(api_key=self._key)
        try:
            completion = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content.strip()
            return _parse_json(raw)
        except Exception as e:
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                raise RateLimitError(f"Groq rate limit: {e}")
            raise InvalidJSONError(f"Groq error: {e}")


# ─── OpenRouter adapter ───────────────────────────────────────────────────────

class OpenRouterClient(LLMClient):
    name = "openrouter"

    def __init__(self, api_key: str):
        self._key = api_key

    def is_available(self) -> bool:
        return bool(self._key)

    def complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict:
        import httpx
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload, timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            return _parse_json(raw)
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                raise RateLimitError(f"OpenRouter rate limit: {e}")
            raise InvalidJSONError(f"OpenRouter error: {e}")


# ─── JSON parsing helper ─────────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _parse_json(raw: str) -> dict | list:
    """Strip markdown fences and parse JSON."""
    fence_match = _FENCE_RE.search(raw)
    if fence_match:
        raw = fence_match.group(1)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise InvalidJSONError(f"JSON parse error: {e} | raw={raw[:200]}")


# ─── Gateway ─────────────────────────────────────────────────────────────────

class Gateway:
    def __init__(self, providers: list[LLMClient], usage: UsageTracker | None = None):
        self._providers = providers
        self._usage = usage or UsageTracker()

    def run(self, system: str, user: str, schema: dict) -> dict | list:
        """Redact, try providers in order, validate, retry once on JSON error."""
        system = redact(system)
        user = redact(user)

        for provider in self._providers:
            if not provider.is_available():
                continue
            for attempt in range(2):
                try:
                    result = provider.complete_json(system, user, schema)
                    self._usage.record(provider.name, ok=True)
                    return result
                except RateLimitError:
                    self._usage.record(provider.name, ok=False)
                    break   # try next provider immediately
                except InvalidJSONError:
                    self._usage.record(provider.name, ok=False)
                    if attempt == 0:
                        continue   # one retry
                    break
                except Exception:
                    self._usage.record(provider.name, ok=False)
                    break

        raise AllProvidersFailed("All LLM providers failed.")

    def available_providers(self) -> list[str]:
        return [p.name for p in self._providers if p.is_available()]


# ─── Factory ─────────────────────────────────────────────────────────────────

_gateway_instance: Gateway | None = None


def get_gateway() -> Gateway:
    global _gateway_instance
    if _gateway_instance is not None:
        return _gateway_instance

    from app.core.setting import settings
    order = [s.strip() for s in settings.llm_provider_order.split(",")]

    provider_map = {
        "claude": lambda: ClaudeClient(settings.anthropic_api_key),
        "gemini": lambda: GeminiClient(settings.google_api_key),
        "groq": lambda: GroqClient(settings.groq_api_key),
        "openrouter": lambda: OpenRouterClient(settings.openrouter_api_key),
    }

    providers = [provider_map[name]() for name in order if name in provider_map]
    _gateway_instance = Gateway(providers)
    return _gateway_instance
