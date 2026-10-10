# 06 Notes Parsing

## Purpose
Turn a month's Apple Notes breakdown (undated, consistent format) into structured `note_line` rows.

## Files
- `services/notes_parser.py`
- `routers/upload.py`: `POST /upload/notes`.

## Function definitions
```python
@dataclass
class ParsedNoteLine:
    item: str; amount: Decimal; category: str | None

def parse_notes_regex(text: str) -> list[ParsedNoteLine]: ...      # primary: consistent format
def parse_notes_llm(text: str) -> list[ParsedNoteLine]: ...        # fallback via 05 gateway
def parse_notes(text: str) -> list[ParsedNoteLine]: ...            # regex first, LLM if low coverage
def validate_lines(lines: list[ParsedNoteLine], declared_total: Decimal | None) -> list[str]: ...  # warnings
def ingest_notes(session: Session, text: str, period: str) -> NotesIngestResult: ...
```

## Flow
upload to `ingest_notes` (dedupe by text hash) to `parse_notes` to map category names to `category` ids to store `note_line` to trigger [07 reconciliation](07-reconciliation.md) for that period.

## Communication
- Calls: `05.gateway` (fallback only), `01` models.
- Called by: `routers/upload.py`. Triggers: `07.reconcile_period`.
- Writes: `source_file(kind=notes)`, `note_line`.

## Tasks
1. Regex parser based on the real sample (item, amount, section headings as categories).
2. LLM fallback with strict schema, used only if regex coverage is below a threshold.
3. Total and sanity validation, with warnings returned to the UI.
4. Re-upload of a changed month replaces that period's lines (versioned by hash).

## Acceptance
- Parsed line total equals the note's own total (when present). A re-upload of identical text changes nothing.
