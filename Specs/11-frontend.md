# 11 Frontend (React + Vite + Recharts)

## Purpose
Upload, review, explore, and ask.

## Structure
```
frontend/src/
├── api.ts                  # typed client for all endpoints
├── pages/ Upload, Review, Dashboard, Compare, Transactions, Chat, Settings
├── components/ CategoryDonut, TrendChart, BudgetBar, TxnTable, ReviewCard, GapTable, RecurringList
└── hooks/ useReviewQueue, useInsights, useReconcile
```

## Pages and the APIs they use
| Page | Shows | Endpoints |
|---|---|---|
| Upload | PDF + password, notes text per month, ingest result and errors | `POST /upload/statement`, `POST /upload/notes` |
| Review Inbox | grouped questions, one-tap options, "apply to all" | `GET /review`, `POST /review/{id}/resolve`, `POST /review/bulk-resolve` |
| Dashboard | category donut, monthly trend, budget bars, recurring, anomalies | `GET /insights/summary`, `/budgets` |
| Compare | noted vs actual per category, matched and unmatched lists | `GET /reconcile/{period}` |
| Transactions | filter/search, inline re-categorise with scope | `GET /transactions`, `PATCH /transactions/{id}` |
| Chat | question box, answer + chart/table | `POST /chat` |
| Settings | categories, budgets, income, LLM provider order, backup | `/budgets`, config endpoints |

## Function-level contracts (`api.ts`)
```ts
uploadStatement(file: File, password: string): Promise<IngestResult>
uploadNotes(text: string, period: string): Promise<NotesIngestResult>
getReview(): Promise<ReviewGroup[]>
resolveReview(id: number, answer: Answer, scope: ApplyScope): Promise<ResolveResult>
getSummary(period: string): Promise<InsightsSummary>
getReconcile(period: string): Promise<ReconcileReport>
patchTxn(id: number, body: TxnPatch): Promise<Txn>
askChat(question: string): Promise<ChatAnswer>
```

## Tasks
1. Vite + TS + Router + Recharts scaffold. 2. Typed API client from the Pydantic schemas (OpenAPI codegen). 3. Review Inbox first (highest value), then Dashboard, Compare, Chat. 4. Empty, loading, and error states everywhere. Badge showing open review count in the nav.

## Acceptance
- The full loop works from the UI: upload, answer questions, see updated dashboard, view the notes vs bank gaps.
