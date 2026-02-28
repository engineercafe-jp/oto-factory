import type {
  GenerateJobResponse,
  GenerateRequest,
  HealthResponse,
  JobStatusResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

interface ApiErrorPayload {
  detail?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new ApiError(payload.detail ?? "API request failed", response.status, payload.detail);
  }

  return (await response.json()) as T;
}

export async function generateMusic(
  payload: GenerateRequest,
  signal?: AbortSignal,
): Promise<GenerateJobResponse> {
  return requestJson<GenerateJobResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });
}

export async function getJobStatus(
  jobId: string,
  signal?: AbortSignal,
): Promise<JobStatusResponse> {
  return requestJson<JobStatusResponse>(`/api/jobs/${jobId}`, {
    method: "GET",
    signal,
  });
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/api/health", {
    method: "GET",
    signal,
  });
}

export async function downloadAudio(jobId: string, signal?: AbortSignal): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/audio`, {
    method: "GET",
    signal,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new ApiError(payload.detail ?? "Audio download failed", response.status, payload.detail);
  }

  return response.blob();
}
