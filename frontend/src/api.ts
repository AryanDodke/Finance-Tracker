const API_URL = "http://localhost:8000";

export async function fetchJson(endpoint: string, options?: RequestInit) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchFormData(endpoint: string, formData: FormData) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

// ─── Upload ─────────────────────────────────────────────────────────────────

export function uploadStatement(file: File, password: string, period: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("password", password);
  formData.append("period", period);
  return fetchFormData("/upload/statement", formData);
}

export function uploadNotes(text: string, period: string) {
  const formData = new FormData();
  formData.append("text", text);
  formData.append("period", period);
  return fetchFormData("/upload/notes", formData);
}

// ─── Transactions ────────────────────────────────────────────────────────────

export function getTransactions(params?: Record<string, any>) {
  const query = new URLSearchParams(params || {}).toString();
  return fetchJson(`/transactions?${query}`);
}

export function patchTransaction(id: number, data: any) {
  return fetchJson(`/transactions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ─── Review ──────────────────────────────────────────────────────────────────

export function getReviewQueue() {
  return fetchJson("/review");
}

export function getReviewCounts() {
  return fetchJson("/review/counts");
}

export function resolveReviewItem(id: number, answer: any, applyScope: string) {
  return fetchJson(`/review/${id}/resolve?apply_scope=${applyScope}`, {
    method: "POST",
    body: JSON.stringify(answer),
  });
}

export function getCategories() {
  return fetchJson("/review/categories");
}

// ─── Insights ────────────────────────────────────────────────────────────────

export function getSummary(period: string) {
  return fetchJson(`/insights/summary?period=${period}`);
}

export function getBudgets() {
  return fetchJson("/insights/budgets");
}

export function upsertBudget(budget: any) {
  return fetchJson("/insights/budgets", {
    method: "PUT",
    body: JSON.stringify(budget),
  });
}

// ─── Reconcile ───────────────────────────────────────────────────────────────

export function getReconcile(period: string) {
  return fetchJson(`/reconcile/${period}`);
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export function askChat(question: string) {
  return fetchJson("/chat", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
