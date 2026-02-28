"use client";

import { useEffect, useState } from "react";

import { AudioPlayer } from "@/components/audio-player";
import { GenerationForm } from "@/components/generation-form";
import { JobStatusCard } from "@/components/job-status-card";
import { ScreenShell } from "@/components/screen-shell";
import { useAudioPlayback } from "@/hooks/use-audio-playback";
import { useGenerationJob } from "@/hooks/use-generation-job";
import { ApiError, getHealth } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";

export default function HomePage() {
  const job = useGenerationJob();
  const audio = useAudioPlayback();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthMessage, setHealthMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    void getHealth(controller.signal)
      .then((response) => {
        setHealth(response);
        setHealthMessage(null);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError) {
          setHealthMessage("バックエンドに接続できない。起動状態を確認してほしい。");
          return;
        }

        setHealthMessage("ヘルスチェックに失敗した。");
      });

    return () => {
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (job.uiStatus !== "downloading" || !job.jobId) {
      return;
    }

    let active = true;

    void audio.loadAudio(job.jobId).then((result) => {
      if (!active) {
        return;
      }

      if (!result.ok) {
        job.markAudioFailure(result.error);
        return;
      }

      job.markAudioReady();
    });

    return () => {
      active = false;
    };
  }, [audio, job]);

  return (
    <ScreenShell
      hero={
        <div className="hero-block">
          <p className="eyebrow">oto-factory</p>
          <h1>作業音を、その場で生成する。</h1>
          <p className="hero-copy">
            プロンプトを送るとバックエンドで非同期ジョブが始まり、進捗を監視しながら
            MP3 の再生までつなぐ。
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
          onPrimePlayback={audio.primeForPlayback}
          onSubmit={job.submit}
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
          />
        </div>
      </div>
    </ScreenShell>
  );
}
