export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

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
  parameters: Record<string, string | number | boolean>;
}

export interface Job {
  id: string;
  name: string;
  status: JobStatus;
  createdAt: string;
  updatedAt: string;
  progress?: number;
  input?: Record<string, unknown>;
  output?: string;
  logs?: string[];
}

export interface CreateJobRequest {
  name: string;
  modelId: string;
  payload: Record<string, unknown>;
}

export interface FileEntry {
  path: string;
  name: string;
  type: 'file' | 'directory';
  size: number;
  modifiedAt: string;
}

export interface JobEvent {
  type: 'job.created' | 'job.updated' | 'job.completed' | 'job.failed';
  payload: Job;
}

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

export class ApiClient {
  private readonly baseUrl: string

  constructor(baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000') {
    this.baseUrl = baseUrl
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
    return this.request<Job[]>('/api/jobs');
  }

  createJob(body: CreateJobRequest) {
    return this.request<Job>('/api/jobs', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  getJob(jobId: string) {
    return this.request<Job>(`/api/jobs/${encodeURIComponent(jobId)}`);
  }

  listFiles(path = '/') {
    const params = new URLSearchParams();
    if (path) {
      params.set('path', path);
    }
    const query = params.toString();
    return this.request<FileEntry[]>(`/api/files${query ? `?${query}` : ''}`);
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
