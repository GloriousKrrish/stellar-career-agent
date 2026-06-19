/**
 * Production-ready Client API Wrapper for Stellar Career Agent API.
 * Connects directly to the FastAPI backend running on http://localhost:8000.
 */

export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("aria.token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

export async function apiRequest(endpoint: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE}${endpoint}`;
  const mergedOptions = {
    ...options,
    headers: {
      ...getHeaders(),
      ...(options.headers || {}),
    },
  };

  const response = await fetch(url, mergedOptions);

  if (!response.ok) {
    let errMsg = "API Request failed";
    try {
      const data = await response.json();
      errMsg = data.detail || errMsg;
    } catch (_) {}
    
    // Auto logout on 401
    if (response.status === 401) {
      if (typeof window !== "undefined") {
        window.localStorage.removeItem("aria.token");
        window.localStorage.removeItem("aria.auth");
        window.localStorage.removeItem("aria.onboarded");
        window.dispatchEvent(new Event("auth-change"));
      }
    }
    throw new Error(errMsg);
  }

  return response.json();
}

// ─── Authentication ──────────────────────────────────────────────────────────

export async function register(name: string, email: string, password: string) {
  const data = await apiRequest("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
  if (typeof window !== "undefined") {
    window.localStorage.setItem("aria.token", data.token);
    window.localStorage.setItem("aria.auth", "1");
    window.dispatchEvent(new Event("auth-change"));
  }
  return data;
}

export async function login(email: string, password: string) {
  const data = await apiRequest("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (typeof window !== "undefined") {
    window.localStorage.setItem("aria.token", data.token);
    window.localStorage.setItem("aria.auth", "1");
    window.dispatchEvent(new Event("auth-change"));
  }
  return data;
}

export async function getMe() {
  return apiRequest("/api/auth/me");
}

export async function logout() {
  try {
    await apiRequest("/api/auth/logout", { method: "POST" });
  } catch (_) {}
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("aria.token");
    window.localStorage.removeItem("aria.auth");
    window.localStorage.removeItem("aria.onboarded");
    window.dispatchEvent(new Event("auth-change"));
  }
}

// ─── Resume ──────────────────────────────────────────────────────────────────

export async function uploadResume(
  file: File,
  autoStart = false,
  role = "",
  remotePreference = "Remote"
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("auto_start_workflow", String(autoStart));
  formData.append("role", role);
  formData.append("remote_preference", remotePreference);

  const token = typeof window !== "undefined" ? window.localStorage.getItem("aria.token") : null;
  const headers: HeadersInit = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/api/resume/upload`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    let errMsg = "Resume upload failed";
    try {
      const data = await response.json();
      errMsg = data.detail || errMsg;
    } catch (_) {}
    throw new Error(errMsg);
  }

  return response.json();
}

export async function getResumeProfile(runId: string) {
  return apiRequest(`/api/resume/${runId}`);
}

// ─── Workflow ────────────────────────────────────────────────────────────────

export async function startWorkflow(params: {
  role: string;
  location?: string;
  remotePreference?: string;
  experienceLevel?: string;
  salaryMin?: number;
  runId?: string;
}) {
  const endpoint = `/api/workflow/start${params.runId ? `?run_id=${encodeURIComponent(params.runId)}` : ""}`;
  return apiRequest(endpoint, {
    method: "POST",
    body: JSON.stringify({
      role: params.role,
      location: params.location || "",
      remote_preference: params.remotePreference || "Remote",
      experience_level: params.experienceLevel || "Mid",
      salary_min: params.salaryMin || 0,
    }),
  });
}

export async function getWorkflow(runId: string) {
  return apiRequest(`/api/workflow/${runId}`);
}

export async function getWorkflowJobs(runId: string, limit = 20, minMatch = 0) {
  return apiRequest(`/api/workflow/${runId}/jobs?limit=${limit}&min_match=${minMatch}`);
}

export async function getWorkflowReport(runId: string) {
  return apiRequest(`/api/workflow/${runId}/report`);
}

export async function listWorkflows() {
  return apiRequest("/api/workflows");
}

// ─── Job Search & Insights ───────────────────────────────────────────────────

export async function searchJobs(role: string, location = "", remotePreference = "Remote", limit = 20) {
  return apiRequest("/api/jobs/search", {
    method: "POST",
    body: JSON.stringify({ role, location, remote_preference: remotePreference, limit }),
  });
}

export async function directSearchJobs(role: string, location = "", salaryTarget = "") {
  return apiRequest("/api/jobs/direct-search", {
    method: "POST",
    body: JSON.stringify({ role, location, salary_target: salaryTarget }),
  });
}

export async function explainJobMatch(runId: string, jobId: string) {
  return apiRequest(`/api/jobs/${runId}/${jobId}/explain`);
}

// ─── Career Coach Chat ────────────────────────────────────────────────────────

export async function sendChatMessage(message: string, history: any[] = [], runId?: string) {
  return apiRequest("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, history, run_id: runId }),
  });
}

export async function getLearningRoadmap(runId: string) {
  return apiRequest(`/api/coach/roadmap?run_id=${runId}`, {
    method: "POST",
  });
}

// ─── Applications Management ──────────────────────────────────────────────────

export async function listApplications() {
  return apiRequest("/api/applications");
}

export async function createOrUpdateApplication(params: {
  job_id: string;
  title: string;
  company: string;
  company_logo?: string;
  stage: string;
  location?: string;
  salary?: string;
  url?: string;
}) {
  return apiRequest("/api/applications", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function deleteApplication(appId: string) {
  return apiRequest(`/api/applications/${appId}`, {
    method: "DELETE",
  });
}

// ─── Agents Status ────────────────────────────────────────────────────────────

export async function getAgentsStatus() {
  return apiRequest("/api/agents/status");
}

// ─── Auto Apply Trigger ───────────────────────────────────────────────────────

export async function applyToJob(runId: string, jobId: string) {
  return apiRequest(`/api/apply/${runId}/${jobId}`, {
    method: "POST",
  });
}
