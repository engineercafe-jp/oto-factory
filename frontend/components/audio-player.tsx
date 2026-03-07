"use client";

import type { LoopStatus } from "@/lib/types";

interface AudioPlayerProps {
  audioRef: (node: HTMLAudioElement | null) => void;
  audioUrl: string | null;
  autoplayBlocked: boolean;
  loading: boolean;
  playManually: () => Promise<void>;
  jobId: string | null;
  onEnded?: () => void;
  loopStatus?: LoopStatus;
  nextTrackReady?: boolean;
  waitingForNext?: boolean;
}

export function AudioPlayer({
  audioRef,
  audioUrl,
  autoplayBlocked,
  loading,
  playManually,
  jobId,
  onEnded,
  loopStatus,
  nextTrackReady,
  waitingForNext,
}: AudioPlayerProps) {
  if (!audioUrl && !loading) {
    return null;
  }

  return (
    <section className="card-oto reveal-card reveal-card--lifted">
      <div className="card-header-row">
        <div>
          <p className="eyebrow">Playback</p>
          <h2>生成された音楽</h2>
        </div>
        <p className="card-lead">生成されたMP3ファイルを再生・ダウンロードできます。</p>
      </div>

      <audio ref={audioRef} controls playsInline preload="metadata" className="audio-element" onEnded={onEnded}>
        {audioUrl ? <source src={audioUrl} type="audio/mpeg" /> : null}
      </audio>

      {loading ? <p className="muted-text">音声を準備しています...</p> : null}

      {autoplayBlocked ? (
        <div className="notice-row" role="status">
          <p>自動再生がブロックされました。下のボタンから再生してください。</p>
          <button type="button" className="ghost-button ghost-button--accent" onClick={() => void playManually()}>
            再生
          </button>
        </div>
      ) : null}

      {loopStatus === "active" && (
        <p className="muted-text">
          {waitingForNext
            ? "次のトラックを準備中です。まもなく再生されます。"
            : nextTrackReady
              ? "次のトラック: 準備完了"
              : "次のトラック: 生成中..."}
        </p>
      )}

      {audioUrl && jobId ? (
        <a className="download-button" href={audioUrl} download={`oto_${jobId}.mp3`}>
          MP3 をダウンロード
        </a>
      ) : null}
    </section>
  );
}
