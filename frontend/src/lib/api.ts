export interface HealthResponse {
  status: string;
  version: string;
}

export interface User {
  id: number;
  email: string;
  role: "admin" | "analyst" | "viewer";
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Connection {
  id: number;
  name: string;
  dialect: string;
  read_only_status: "verified" | "writable" | "unknown";
}

export interface LLMStatus {
  provider: string;
  model: string;
  reachable: boolean;
  latency_ms: number;
}

export interface QueryResult {
  audit_event_id: number;
  question: string;
  sql: string | null;
  columns: string[];
  rows: unknown[][];
  summary: string | null;
  summary_reason: string | null;
  followups: string[];
  tables_touched: string[];
  attempts: number;
  unanswerable: boolean;
  unanswerable_reason: string | null;
  duration_ms: number;
}

export interface AuditEvent {
  id: number;
  ts: string;
  user_id: number;
  connection_id: number;
  question: string;
  sql: string | null;
  tables_touched: string[];
  row_count: number;
  duration_ms: number;
  provider: string;
  model: string;
  attempts: number;
  outcome: string;
  blocked_reason: string | null;
  summary_sent_to_cloud: boolean;
}

export interface AuditPage {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface AISettings {
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  has_api_key: boolean;
  cloud_summaries_enabled: boolean;
  pii_redaction_enabled: boolean;
}

export interface SchemaColumn {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
  foreign_key_targets: string[];
  description: string;
}

export interface SchemaTable {
  name: string;
  columns: SchemaColumn[];
  description: string;
}

export interface Permission {
  role: "analyst" | "viewer";
  table_name: string;
  column_name: string | null;
  visible: boolean;
}

export interface SchemaConfig {
  tables: SchemaTable[];
  permissions: Permission[];
}

const TOKEN_KEY = "text2sql_token";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY);
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (response.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event("auth:expired"));
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health", { signal });
}

export const api = {
  auth: (mode: "login" | "register", email: string, password: string) =>
    apiFetch<AuthResponse>(`/api/auth/${mode}`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => apiFetch<User>("/api/auth/me"),
  llmStatus: () => apiFetch<LLMStatus>("/api/llm/status"),
  connections: () => apiFetch<Connection[]>("/api/connections"),
  createConnection: (input: { name: string; dialect: string; url: string }) =>
    apiFetch<Connection>("/api/connections", { method: "POST", body: JSON.stringify(input) }),
  samples: (id: number) =>
    apiFetch<{ questions: string[] }>(`/api/connections/${id}/samples`),
  readonlySnippet: (id: number) =>
    apiFetch<{ dialect: string; sql: string }>(`/api/connections/${id}/readonly-snippet`),
  query: (question: string, connection_id: number) =>
    apiFetch<QueryResult>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question, connection_id }),
    }),
  history: () => apiFetch<AuditPage>("/api/audit/me"),
  audit: () => apiFetch<AuditPage>("/api/audit"),
  downloadAudit: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    const response = await fetch("/api/audit?format=csv", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error("Audit export failed");
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "audit.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  },
  aiSettings: () => apiFetch<AISettings>("/api/admin/ai"),
  updateAISettings: (input: Omit<AISettings, "has_api_key"> & { llm_api_key: string }) =>
    apiFetch<AISettings>("/api/admin/ai", { method: "PUT", body: JSON.stringify(input) }),
  schema: (connectionId: number) =>
    apiFetch<SchemaConfig>(`/api/admin/schema/${connectionId}`),
  updateSchema: (connectionId: number, permissions: Permission[]) =>
    apiFetch<SchemaConfig>(`/api/admin/schema/${connectionId}`, {
      method: "PUT",
      body: JSON.stringify(permissions),
    }),
};

export { TOKEN_KEY };
