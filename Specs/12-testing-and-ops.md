# 12 Testing and Operations

## Testing
| Layer | What | Tools |
|---|---|---|
| Parser | golden-file tests with redacted SBI PDFs; narration regex table tests | pytest |
| Normalisation | variant and confusable-pair tests | pytest |
| Categoriser | rule priority, confidence routing, LLM mocked | pytest + fake `LLMClient` |
| Gateway | provider failure simulation, invalid JSON repair, redaction assertions | pytest |
| Reconciler | synthetic months with planted mismatches | pytest |
| Insights | seeded recurring and outliers | pytest |
| API | endpoint contract tests | FastAPI `TestClient` |
| Frontend | key flows (review resolve, upload) | Vitest + Testing Library |

## Fixtures
- `tests/fixtures/`: redacted statement PDFs, notes samples, `FakeLLM` returning canned JSON.

## Operations
- `make dev` runs backend + frontend. `make test`, `make lint`.
- Config via `.env`: provider keys and order, thresholds (`CONF_AUTO=0.8`, `MATCH_MIN=0.7`, gap thresholds).
- Backup: copy `spend.db` and uploaded files to a dated folder. Export CSV of transactions and rules.
- Secrets never committed. PDFs and DB git-ignored. PDF passwords are never stored.

## Definition of Done (per feature)
Signatures match its doc, unit tests pass, errors handled and surfaced, doc updated, acceptance bullets verified.
