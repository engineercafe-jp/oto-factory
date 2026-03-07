"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AudioPlayer } from "@/components/audio-player";
import { GenerationForm } from "@/components/generation-form";
import { JobStatusCard } from "@/components/job-status-card";
import { ScreenShell } from "@/components/screen-shell";
import { useAudioPlayback } from "@/hooks/use-audio-playback";
import { useGenerationJob } from "@/hooks/use-generation-job";
import { useLoopGeneration } from "@/hooks/use-loop-generation";
import { ApiError, getHealth } from "@/lib/api";
import type { GenerateRequest, HealthResponse } from "@/lib/types";

export default function HomePage() {
  const job = useGenerationJob();
  const audio = useAudioPlayback();
  const loop = useLoopGeneration();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthMessage, setHealthMessage] = useState<string | null>(null);
  const requestedAudioJobIdRef = useRef<string | null>(null);
  const formPayloadRef = useRef<GenerateRequest | null>(null);
  const { isBusy, jobId, uiStatus, markAudioFailure, markAudioReady } = job;
  const isLoopActive = loop.loopStatus !== "inactive";

  useEffect(() => {
    let active = true;
    let currentController: AbortController | null = null;
    let intervalId: number | null = null;

    const runHealthCheck = async () => {
      currentController?.abort();
      const controller = new AbortController();
      currentController = controller;

      try {
        const response = await getHealth(controller.signal);
        if (!active) {
          return;
        }

        setHealth(response);
        setHealthMessage(null);
      } catch (error: unknown) {
        if (!active || controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError) {
          setHealthMessage("サーバーに接続できませんでした。バックエンドが起動しているかご確認ください。");
          return;
        }

        setHealthMessage("サーバーの状態を確認できませんでした。");
      }
    };

    void runHealthCheck();

    if (!isBusy) {
      intervalId = window.setInterval(() => {
        void runHealthCheck();
      }, 30000);
    }

    return () => {
      active = false;
      currentController?.abort();
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
    };
  }, [isBusy]);

  useEffect(() => {
    // ループ中は独自にダウンロード・再生を管理する
    if (isLoopActive) return;

    if (uiStatus !== "downloading" || !jobId) {
      if (uiStatus === "idle" || uiStatus === "failed" || uiStatus === "completed") {
        requestedAudioJobIdRef.current = null;
      }
      return;
    }

    if (requestedAudioJobIdRef.current === jobId) {
      return;
    }

    requestedAudioJobIdRef.current = jobId;
    const currentJobId = jobId;

    void audio.loadAudio(currentJobId).then((result) => {
      if (requestedAudioJobIdRef.current !== currentJobId) {
        return;
      }

      if (!result.ok) {
        markAudioFailure(result.error);
        return;
      }

      markAudioReady();
    });

    return undefined;
  }, [audio, isLoopActive, jobId, markAudioFailure, markAudioReady, uiStatus]);

  const handleFormChange = useCallback((payload: GenerateRequest) => {
    formPayloadRef.current = payload;
  }, []);

  const handleLoopStart = useCallback(
    (payload: GenerateRequest) => {
      void loop.startLoop(payload, audio, () => formPayloadRef.current ?? payload);
    },
    [loop, audio],
  );

  return (
    <ScreenShell
      hero={
        <div className="hero-block">
          <p className="eyebrow">oto-factory</p>
          <h1>作業用BGMを、今すぐ。</h1>
          <p className="hero-copy">
            テキストで雰囲気を伝えるだけで、AIが音楽を生成します。
            完成したらすぐに再生・ダウンロードできます。
          </p>

          <div className="hero-status">
            <div className="hero-status__item">
              <span>server</span>
              <strong>{health?.status === "ok" ? "online" : "offline"}</strong>
            </div>
            <div className="hero-status__item">
              <span>gpu</span>
              <strong>{health?.gpu ?? "-"}</strong>
            </div>
            <div className="hero-status__item">
              <span>queue</span>
              <strong>{health?.queue_size ?? "-"}</strong>
            </div>
          </div>

          {healthMessage ? <p className="hero-warning">{healthMessage}</p> : null}
        </div>
      }
    >
      <div className="layout-grid">
        <GenerationForm
          disabled={job.isBusy}
          loopStatus={loop.loopStatus}
          onPrimePlayback={audio.primeForPlayback}
          onSubmit={job.submit}
          onLoopStart={handleLoopStart}
          onLoopStop={loop.stopLoop}
          onFormChange={handleFormChange}
        />

        <div className="stack">
          <JobStatusCard
            uiStatus={job.uiStatus}
            job={job.job}
            message={job.responseMessage}
            error={job.error}
          />
          <AudioPlayer
            audioRef={audio.attachAudioRef}
            audioUrl={audio.audioUrl}
            autoplayBlocked={audio.autoplayBlocked}
            loading={audio.loading}
            playManually={audio.playManually}
            jobId={job.jobId}
            onEnded={isLoopActive ? loop.onTrackEnded : undefined}
            loopStatus={loop.loopStatus}
            nextTrackReady={loop.nextTrackReady}
            waitingForNext={loop.waitingForNext}
          />
        </div>
      </div>
    </ScreenShell>
  );
}
