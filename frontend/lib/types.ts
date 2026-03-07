export type JobStatus = "queued" | "running" | "completed" | "failed";

export type LoopStatus = "inactive" | "active" | "stopping";

export type UiStatus =
  | "idle"
  | "submitting"
  | "queued"
  | "running"
  | "downloading"
  | "completed"
  | "failed";

export interface GenerateRequest {
  prompt: string;
  duration: number;
  bpm?: number | null;
  seed?: number | null;
}

export interface GenerateJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number | null;
  stage: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  gpu: string;
  vram_gb: number;
  queue_size: number;
}

export interface UiError {
  summary: string;
  detail?: string | null;
}
