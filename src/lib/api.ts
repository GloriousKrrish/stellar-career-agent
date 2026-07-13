// API helper for communicating with the FastAPI backend
//
// Priority:
//  1. VITE_BACKEND_URL (set in Vercel env vars for production)
//  2. localhost:8000 (automatic for local development)

const getBaseUrl = (): string => {
  // Injected at build time by Vite — set VITE_BACKEND_URL in Vercel project settings
  if (import.meta.env.VITE_BACKEND_URL) {
    return String(import.meta.env.VITE_BACKEND_URL).replace(/\/$/, "");
  }
  if (typeof window === "undefined") return "";
  // Local dev: frontend is on 8080, backend is on 8000
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }
  // Production without explicit env var — use relative (same-origin Vercel function)
  return "";
};

export const API_BASE_URL = getBaseUrl();

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("aria.token");
}

export function setToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("aria.token", token);
  window.localStorage.setItem("aria.auth", "1");
}

export function clearToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("aria.token");
  window.localStorage.removeItem("aria.auth");
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      clearToken();
      window.localStorage.removeItem("aria.user");
      window.location.href = "/auth/login";
    }
    let errMsg = "API Request failed";
    try {
      const errData = await response.json();
      errMsg = errData?.detail || errData?.message || errMsg;
    } catch {
      // ignore
    }
    throw new Error(errMsg);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Auth
  async register(name: string, email: string, password: string) {
    const data = await request<{ token: string; user: any }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    setToken(data.token);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("aria.user", JSON.stringify(data.user));
    }
    return data;
  },

  async login(email: string, password: string) {
    const data = await request<{ token: string; user: any }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.token);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("aria.user", JSON.stringify(data.user));
    }
    return data;
  },

  async getMe() {
    const user = await request<any>("/api/auth/me");
    if (typeof window !== "undefined") {
      window.localStorage.setItem("aria.user", JSON.stringify(user));
    }
    return user;
  },

  // Resume Upload
  async uploadResume(file: File, autoStartWorkflow: boolean = false, role: string = "", remotePreference: string = "Remote") {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("auto_start_workflow", String(autoStartWorkflow));
    formData.append("role", role);
    formData.append("remote_preference", remotePreference);

    return request<any>("/api/resume/upload", {
      method: "POST",
      body: formData,
    });
  },

  // Workflows & Agents
  async startWorkflow(role: string, remotePreference: string = "Remote", runId?: string, location: string = "", salaryMin: number = 0, salaryMax: number = 5000000) {
    return request<any>("/api/workflow/start", {
      method: "POST",
      body: JSON.stringify({
        role,
        remote_preference: remotePreference,
        run_id: runId,
        location,
        salary_min: salaryMin,
        salary_max: salaryMax,
      }),
    });
  },

  async getWorkflowState(runId: string) {
    return request<any>(`/api/workflow/${runId}`);
  },

  async getWorkflows() {
    return request<{ total: number; workflows: any[] }>("/api/workflows");
  },

  async getWorkflowJobs(runId: string, limit: number = 20, minMatch: number = 0) {
    return request<{ run_id: string; total: number; jobs: any[] }>(`/api/workflow/${runId}/jobs?limit=${limit}&min_match=${minMatch}`);
  },

  async getAgentStatus() {
    return request<{ agents: any[]; total: number; active: number }>("/api/agents/status");
  },
  
  async getAgentsDashboard() {
    return request<{ agents: any[] }>("/api/agents/dashboard");
  },

  // Applications
  async getApplications() {
    return request<{ applications: any[] }>("/api/applications");
  },

  async createApplication(application: {
    job_id: string;
    title: string;
    company: string;
    company_logo?: string;
    stage: string;
    location?: string;
    salary?: string;
    url?: string;
  }) {
    return request<any>("/api/applications", {
      method: "POST",
      body: JSON.stringify(application),
    });
  },

  async deleteApplication(appId: string) {
    return request<any>(`/api/applications/${appId}`, {
      method: "DELETE",
    });
  },

  // Direct Job Search
  async directJobSearch(role: string, location: string = "", salaryTarget: string = "") {
    return request<{ jobs: any[] }>("/api/jobs/direct-search", {
      method: "POST",
      body: JSON.stringify({ role, location, salary_target: salaryTarget }),
    });
  },

  // AutoApply Pipeline
  async getAutoApplyStats() {
    return request<{
      stats: Record<string, number>;
      total: number;
      applied: number;
      pending: number;
      manual: number;
      failed: number;
    }>("/api/autoapply/stats");
  },

  async getAutoApplyQueue(limit: number = 50) {
    return request<{ entries: any[]; total: number }>(`/api/autoapply/queue?limit=${limit}`);
  },

  async enqueueForAutoApply(data: {
    run_id: string;
    job_id: string;
    job_title: string;
    job_company: string;
    job_url: string;
    job_source?: string;
  }) {
    return request<{ status: string; queue_id: string; message: string }>("/api/autoapply/enqueue", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
