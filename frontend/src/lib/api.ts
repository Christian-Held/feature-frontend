export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface EnvVariable {
  key: string;
  value: string;
  description?: string;
  isSecret?: boolean;
}

export interface ModelVariant {
  id: string;
  label: string;
  description?: string;
}

export interface ModelConfig {
  id: string;
  name: string;
  provider: string;
  description?: string;
  variants: ModelVariant[];
  selectedVariant?: string;
  parameters: Record<string, string>;
}

export interface BudgetGuard {
  budget_usd_max: number;
  max_requests: number;
  max_wallclock_minutes: number;
}

export interface HealthResponse {
  ok: boolean;
  db: boolean;
  redis: boolean;
  version: string;
  budgetGuard: BudgetGuard;
}

export interface Job {
  id: string;
  status: JobStatus;
  task: string;
  repo_owner: string;
  repo_name: string;
  branch_base: string;
  budget_usd: number;
  max_requests: number;
  max_minutes: number;
  model_cto?: string | null;
  model_coder?: string | null;
  cost_usd: number;
  tokens_in: number;
  tokens_out: number;
  requests_made: number;
  progress: number;
  last_action?: string | null;
  pr_links: string[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CreateTaskRequest {
  task: string;
  repo_owner: string;
  repo_name: string;
  branch_base: string;
  budgetUsd: number;
  maxRequests: number;
  maxMinutes: number;
  modelCTO?: string;
  modelCoder?: string;
}

export interface FileEntry {
  path: string;
  name: string;
  type: 'file' | 'directory';
  size: number;
  modifiedAt: string;
}

export interface JobEvent {
  type: 'job.created' | 'job.updated' | 'job.completed' | 'job.failed' | 'job.cancelled';
  payload: Job;
}

export interface AccountPlanResponse {
  plan: 'FREE' | 'PRO';
  name: string;
  monthly_price_usd: string;
}

export interface AccountPlanUpdateRequest {
  plan: 'FREE' | 'PRO';
}

export interface AccountLimitsResponse {
  monthly_cap_usd: string;
  hard_stop: boolean;
  usage_usd: string;
  remaining_usd: string;
  cap_reached: boolean;
}

export interface AccountLimitsUpdateRequest {
  monthly_cap_usd: string | number;
  hard_stop: boolean;
}

export type AdminUserStatus = 'ACTIVE' | 'UNVERIFIED' | 'DISABLED';
export type AdminRole = 'ADMIN' | 'USER' | 'BILLING_ADMIN' | 'SUPPORT';
export type AdminUserSort = 'created_at_desc' | 'created_at_asc';

export interface AdminUserSummary {
  id: string;
  email: string;
  status: AdminUserStatus;
  roles: AdminRole[];
  created_at: string;
  mfa_enabled: boolean;
  email_verified: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface AdminUsersQuery {
  q?: string;
  status?: AdminUserStatus;
  role?: AdminRole;
  page?: number;
  page_size?: number;
  sort?: AdminUserSort;
}

export interface AdminUserActionResponse {
  user: AdminUserSummary;
}

export interface ResendVerificationActionResponse {
  message: string;
}

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  ip: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogQuery {
  actor?: string;
  action?: string;
  target_type?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 500) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

export class ApiClient {
  private readonly baseUrl: string

  constructor(baseUrl = import.meta.env.VITE_API_BASE_URL ?? '') {
    this.baseUrl = baseUrl.replace(/\/$/, '')
  }

  private get headers(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    // Add Authorization header if we have an access token
    // Import dynamically to avoid circular dependencies
    try {
      const authState = localStorage.getItem('auth-storage')
      if (authState) {
        const parsed = JSON.parse(authState)
        if (parsed?.state?.accessToken) {
          headers['Authorization'] = `Bearer ${parsed.state.accessToken}`
        }
      }
    } catch (e) {
      // Ignore errors reading auth state
    }

    return headers
  }

  private async requestRaw(path: string, options: RequestOptions = {}): Promise<Response> {
    const baseHeaders = options.body instanceof FormData ? {} : this.headers

    return fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        ...baseHeaders,
        ...options.headers,
      },
    })
  }

  async requestWithMetadata<T>(path: string, options: RequestOptions = {}): Promise<{ data: T; status: number; warning?: string }>
  {
    const response = await this.requestRaw(path, options);
    const warning = response.headers.get('X-Spend-Warning') ?? undefined;

    if (!response.ok) {
      const message = await response.text();
      throw new ApiError(message || `Request failed with status ${response.status}`, response.status);
    }

    if (response.status === 204) {
      return { data: undefined as T, status: response.status, warning };
    }

    const data = (await response.json()) as T;
    return { data, status: response.status, warning };
  }

  private prepareBody(body: unknown, fallback?: BodyInit | null): BodyInit | null | undefined {
    if (body === undefined) {
      return fallback
    }

    if (
      typeof body === 'string' ||
      body instanceof FormData ||
      body instanceof URLSearchParams ||
      body instanceof Blob ||
      body instanceof ArrayBuffer ||
      ArrayBuffer.isView(body)
    ) {
      return body as BodyInit
    }

    if (body === null) {
      return null
    }

    return JSON.stringify(body)
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await this.requestRaw(path, options)

    if (!response.ok) {
      const message = await response.text();
      throw new ApiError(message || `Request failed with status ${response.status}`, response.status);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T
  }

  get<T>(path: string, options: RequestOptions = {}) {
    return this.request<T>(path, { ...options, method: options.method ?? 'GET' })
  }

  getRaw(path: string, options: RequestOptions = {}) {
    return this.requestRaw(path, { ...options, method: options.method ?? 'GET' })
  }

  post<T, B = unknown>(path: string, body?: B, options: RequestOptions = {}) {
    const { body: originalBody, ...rest } = options
    const preparedBody = this.prepareBody(body, originalBody ?? null)
    return this.request<T>(path, { ...rest, method: 'POST', body: preparedBody ?? undefined })
  }

  put<T, B = unknown>(path: string, body?: B, options: RequestOptions = {}) {
    const { body: originalBody, ...rest } = options
    const preparedBody = this.prepareBody(body, originalBody ?? null)
    return this.request<T>(path, { ...rest, method: 'PUT', body: preparedBody ?? undefined })
  }

  patch<T, B = unknown>(path: string, body?: B, options: RequestOptions = {}) {
    const { body: originalBody, ...rest } = options
    const preparedBody = this.prepareBody(body, originalBody ?? null)
    return this.request<T>(path, { ...rest, method: 'PATCH', body: preparedBody ?? undefined })
  }

  delete<T, B = unknown>(path: string, body?: B, options: RequestOptions = {}) {
    const { body: originalBody, ...rest } = options
    const preparedBody = this.prepareBody(body, originalBody ?? null)
    return this.request<T>(path, { ...rest, method: 'DELETE', body: preparedBody ?? undefined })
  }

  getEnvVariables() {
    return this.request<EnvVariable[]>('/api/env');
  }

  updateEnvVariable(key: string, value: string) {
    return this.request<EnvVariable>(`/api/env/${encodeURIComponent(key)}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    });
  }

  listModels() {
    return this.request<ModelConfig[]>('/api/models');
  }

  updateModelConfig(modelId: string, payload: Partial<ModelConfig>) {
    return this.request<ModelConfig>(`/api/models/${encodeURIComponent(modelId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  listJobs() {
    return this.request<Job[]>('/jobs');
  }

  createTask(body: CreateTaskRequest) {
    return this.request<{ job_id: string }>('/tasks', {
      method: 'POST',
      body: JSON.stringify(body),
    }).then((response) => this.getJob(response.job_id));
  }

  listBranches(owner: string, repo: string) {
    const params = new URLSearchParams({ owner, repo });
    return this.request<{ branches: string[] }>(`/api/github/branches?${params.toString()}`);
  }

  getJob(jobId: string) {
    return this.request<Job>(`/jobs/${encodeURIComponent(jobId)}`);
  }

  listFiles(path = '/') {
    const params = new URLSearchParams();
    if (path) {
      params.set('path', path);
    }
    const query = params.toString();
    return this.request<FileEntry[]>(`/api/files${query ? `?${query}` : ''}`);
  }

  getHealth() {
    return this.request<HealthResponse>('/health/');
  }

  getAccountPlan() {
    return this.requestWithMetadata<AccountPlanResponse>('/v1/account/plan');
  }

  updateAccountPlan(body: AccountPlanUpdateRequest) {
    return this.requestWithMetadata<AccountPlanResponse>('/v1/account/plan', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  getAccountLimits() {
    return this.requestWithMetadata<AccountLimitsResponse>('/v1/account/limits');
  }

  updateAccountLimits(body: AccountLimitsUpdateRequest) {
    return this.requestWithMetadata<AccountLimitsResponse>('/v1/account/limits', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  listAdminUsers(params: AdminUsersQuery = {}) {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.status) search.set('status', params.status);
    if (params.role) search.set('role', params.role);
    if (params.page) search.set('page', String(params.page));
    if (params.page_size) search.set('page_size', String(params.page_size));
    if (params.sort) search.set('sort', params.sort);
    const query = search.toString();
    return this.request<PaginatedResponse<AdminUserSummary>>(
      `/v1/admin/users${query ? `?${query}` : ''}`,
    );
  }

  updateAdminUserRoles(userId: string, roles: AdminRole[]) {
    return this.request<AdminUserSummary>(`/v1/admin/users/${encodeURIComponent(userId)}/roles`, {
      method: 'POST',
      body: JSON.stringify({ roles }),
    });
  }

  lockAdminUser(userId: string) {
    return this.request<AdminUserActionResponse>(`/v1/admin/users/${encodeURIComponent(userId)}/lock`, {
      method: 'POST',
    });
  }

  unlockAdminUser(userId: string) {
    return this.request<AdminUserActionResponse>(`/v1/admin/users/${encodeURIComponent(userId)}/unlock`, {
      method: 'POST',
    });
  }

  resetAdminUserTwoFactor(userId: string) {
    return this.request<AdminUserActionResponse>(`/v1/admin/users/${encodeURIComponent(userId)}/reset-2fa`, {
      method: 'POST',
    });
  }

  resendAdminVerification(userId: string) {
    return this.request<ResendVerificationActionResponse>(
      `/v1/admin/users/${encodeURIComponent(userId)}/resend-verification`,
      {
        method: 'POST',
      },
    );
  }

  listAuditLogs(params: AuditLogQuery = {}) {
    const search = new URLSearchParams();
    if (params.actor) search.set('actor', params.actor);
    if (params.action) search.set('action', params.action);
    if (params.target_type) search.set('target_type', params.target_type);
    if (params.from) search.set('from', params.from);
    if (params.to) search.set('to', params.to);
    if (params.page) search.set('page', String(params.page));
    if (params.page_size) search.set('page_size', String(params.page_size));
    const query = search.toString();
    return this.request<PaginatedResponse<AuditLogEntry>>(
      `/v1/admin/audit-logs${query ? `?${query}` : ''}`,
    );
  }

  exportAuditLogsCsv(params: AuditLogQuery = {}) {
    const search = new URLSearchParams({ format: 'csv' });
    if (params.actor) search.set('actor', params.actor);
    if (params.action) search.set('action', params.action);
    if (params.target_type) search.set('target_type', params.target_type);
    if (params.from) search.set('from', params.from);
    if (params.to) search.set('to', params.to);
    const query = search.toString();
    return this.requestRaw(`/v1/admin/audit-logs/export?${query}`, {
      headers: { Accept: 'text/csv' },
    });
  }

  get websocketUrl() {
    const wsFromEnv = import.meta.env.VITE_WS_URL;
    if (wsFromEnv) {
      return wsFromEnv;
    }

    // Handle empty baseUrl by using window.location
    if (!this.baseUrl) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}/ws/jobs`;
    }

    const url = new URL(this.baseUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/ws/jobs';
    url.search = '';
    return url.toString();
  }
}

export const apiClient = new ApiClient()

export default apiClient
