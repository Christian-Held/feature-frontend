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

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

export class ApiClient {
  private readonly baseUrl: string

  constructor(baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5173') {
    this.baseUrl = baseUrl.replace(/\/$/, '')
  }

  private get headers(): HeadersInit {
    return {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed with status ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
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
    })
      .then((response) => this.getJob(response.job_id));
  }

  listBranches(owner: string, repo: string) {
    const params = new URLSearchParams({
      owner,
      repo,
    });
    return this.request<{ branches: string[] }>(
      `/api/github/branches?${params.toString()}`,
    );
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

  get websocketUrl() {
    const wsFromEnv = import.meta.env.VITE_WS_URL;
    if (wsFromEnv) {
      return wsFromEnv;
    }

    const url = new URL(this.baseUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/ws/jobs';
    url.search = '';
    return url.toString();
  }
}

export const apiClient = new ApiClient();
