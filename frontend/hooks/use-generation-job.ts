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
        summary: "ただいまサーバーが混み合っています。しばらく経ってから再度お試しください。",
        detail: error.detail,
      };
    }

    if (error.status === 404) {
      return {
        summary: "ジョブが見つかりませんでした。有効期限切れの可能性があります。",
        detail: error.detail,
      };
    }

    return {
      summary: "サーバーとの通信に失敗しました。バックエンドが起動しているかご確認ください。",
      detail: error.detail,
    };
  }

  return {
    summary: "予期しないエラーが発生しました。しばらく経ってから再度お試しください。",
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
                  summary: "生成中にエラーが発生しました。内容をご確認のうえ、再度お試しください。",
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
          stage: "リクエストを受け付けました",
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
        summary: "音声の取得に失敗しました。しばらく経ってから再度お試しください。",
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
