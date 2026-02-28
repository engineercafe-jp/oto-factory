"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, generateMusic, getJobStatus } from "@/lib/api";
import type { GenerateRequest, JobStatusResponse, UiError, UiStatus } from "@/lib/types";

interface GenerationJobState {
  uiStatus: UiStatus;
  job: JobStatusResponse | null;
  jobId: string | null;
  responseMessage: string | null;
  error: UiError | null;
}

const INITIAL_STATE: GenerationJobState = {
  uiStatus: "idle",
  job: null,
  jobId: null,
  responseMessage: null,
  error: null,
};

function mapApiError(error: unknown): UiError {
  if (error instanceof ApiError) {
    if (error.status === 503) {
      return {
        summary: "現在キューが混雑している。少し待ってから再試行してほしい。",
        detail: error.detail,
      };
    }

    if (error.status === 404) {
      return {
        summary: "ジョブが見つからない。期限切れか無効な ID の可能性がある。",
        detail: error.detail,
      };
    }

    return {
      summary: "サーバーとの通信に失敗した。バックエンドの起動状態を確認してほしい。",
      detail: error.detail,
    };
  }

  return {
    summary: "不明なエラーが発生した。時間をおいて再試行してほしい。",
  };
}

export function useGenerationJob() {
  const [state, setState] = useState<GenerationJobState>(INITIAL_STATE);
  const pollingAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      pollingAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (!state.jobId || (state.uiStatus !== "queued" && state.uiStatus !== "running")) {
      return;
    }

    const jobId = state.jobId;
    let timeoutId: number | null = null;

    const schedulePoll = (delay: number) => {
      timeoutId = window.setTimeout(() => {
        void pollOnce();
      }, delay);
    };

    const pollOnce = async () => {
      pollingAbortRef.current?.abort();
      const controller = new AbortController();
      pollingAbortRef.current = controller;

      try {
        const job = await getJobStatus(jobId, controller.signal);
        setState((current) => ({
          ...current,
          jobId: job.job_id,
          job,
          uiStatus:
            job.status === "completed"
              ? "downloading"
              : job.status === "failed"
                ? "failed"
                : job.status,
          error:
            job.status === "failed"
              ? {
                  summary: "生成に失敗した。内容を確認して再送してほしい。",
                  detail: job.error,
                }
              : current.error,
        }));

        if (job.status === "queued" || job.status === "running") {
          schedulePoll(document.visibilityState === "visible" ? 2000 : 5000);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setState((current) => ({
          ...current,
          uiStatus: "failed",
          error: mapApiError(error),
        }));
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        if (timeoutId !== null) {
          window.clearTimeout(timeoutId);
        }
        void pollOnce();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    void pollOnce();

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      pollingAbortRef.current?.abort();
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [state.jobId, state.uiStatus]);

  const submit = async (payload: GenerateRequest) => {
    pollingAbortRef.current?.abort();
    setState({
      uiStatus: "submitting",
      job: null,
      jobId: null,
      responseMessage: null,
      error: null,
    });

    try {
      const response = await generateMusic(payload);
      setState({
        uiStatus: response.status,
        job: {
          job_id: response.job_id,
          status: response.status,
          progress: 0,
          stage: "ジョブをキューに投入した",
          created_at: new Date().toISOString(),
          completed_at: null,
          error: null,
        },
        jobId: response.job_id,
        responseMessage: response.message,
        error: null,
      });
    } catch (error) {
      setState({
        ...INITIAL_STATE,
        uiStatus: "failed",
        error: mapApiError(error),
      });
    }
  };

  const markAudioReady = () => {
    setState((current) => ({
      ...current,
      uiStatus: "completed",
      error: null,
    }));
  };

  const markAudioFailure = (detail: string) => {
    setState((current) => ({
      ...current,
      uiStatus: "failed",
      error: {
        summary: "音声の取得に失敗した。時間をおいて再試行してほしい。",
        detail,
      },
    }));
  };

  return {
    ...state,
    isBusy:
      state.uiStatus === "submitting" ||
      state.uiStatus === "queued" ||
      state.uiStatus === "running" ||
      state.uiStatus === "downloading",
    submit,
    markAudioReady,
    markAudioFailure,
  };
}
