# 05 LLM Gateway

## Purpose
One interface to all LLMs with ordered fallback, redaction, schema validation, and rate-limit awareness. No other feature talks to a provider directly.

## Files
- `llm/base.py`: `LLMClient` protocol, exceptions.
- `llm/claude.py`, `llm/gemini.py`, `llm/groq.py`, `llm/openrouter.py`: adapters.
- `llm/gateway.py`: fallback orchestration.
- `llm/redactor.py`: strips sensitive data.
- `llm/usage.py`: per-provider counters.

## Function definitions
```python
# base.py
class LLMClient(Protocol):
    name: str
    def complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict: ...

class RateLimitError(Exception): ...
class InvalidJSONError(Exception): ...
class AllProvidersFailed(Exception): ...

# redactor.py
def redact(text: str) -> str: ...                  # account nos, phones, UPI IDs, balances, long digit runs
def redact_names(text: str, known_names: list[str]) -> str: ...

# gateway.py
class Gateway:
    def __init__(self, providers: list[LLMClient], usage: UsageTracker): ...
    def run(self, system: str, user: str, schema: dict) -> dict: ...   # redact, try in order, validate, retry
    def available_providers(self) -> list[str]: ...

def get_gateway() -> Gateway: ...                  # built from config order

# usage.py
class UsageTracker:
    def record(self, provider: str, ok: bool) -> None: ...
    def remaining(self, provider: str) -> int | None: ...
```

## Behaviour
Order from `.env` (default Claude, Gemini, Groq, OpenRouter). On `RateLimitError`, timeout, or `InvalidJSONError` (after one repair retry), move to the next provider. If all fail, raise `AllProvidersFailed` and callers degrade gracefully (create review items instead).

## Communication
- Called by: `04.categoriser`, `06.notes_parser`, `10.qa`.
- Calls: provider SDKs/HTTP, `usage`.
- Writes: `llm_usage`.

## Tasks
1. Protocol and adapters (one per provider, same JSON contract).
2. JSON-mode / schema enforcement per provider, with fence-stripping and `jsonschema` validation.
3. Redactor with unit tests (no digits runs over 6, no `@handle`).
4. Backoff, timeouts, daily counters, config-driven order.

## Acceptance
- Killing the primary provider (simulate errors) still returns valid output from a fallback. Redactor leaves no account numbers or UPI IDs in any outbound prompt (asserted in tests).
