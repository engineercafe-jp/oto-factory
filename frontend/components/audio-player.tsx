"use client";

interface AudioPlayerProps {
  audioRef: (node: HTMLAudioElement | null) => void;
  audioUrl: string | null;
  autoplayBlocked: boolean;
  loading: boolean;
  playManually: () => Promise<void>;
  jobId: string | null;
}

export function AudioPlayer({
  audioRef,
  audioUrl,
  autoplayBlocked,
  loading,
  playManually,
  jobId,
}: AudioPlayerProps) {
  if (!audioUrl && !loading) {
    return null;
  }

  return (
    <section className="card stack reveal-card reveal-card--lifted">
      <div className="card__header">
        <div>
          <p className="eyebrow">Playback</p>
          <h2>生成結果</h2>
        </div>
        <p className="card__lead">再生と保存は同じ MP3 を使う。</p>
      </div>

      <audio ref={audioRef} controls playsInline preload="metadata" className="audio-element">
        {audioUrl ? <source src={audioUrl} type="audio/mpeg" /> : null}
      </audio>

      {loading ? <p className="muted-text">音声を取得している...</p> : null}

      {autoplayBlocked ? (
        <div className="notice-row" role="status">
          <p>生成は完了したが、自動再生できなかった。再生ボタンを押してほしい。</p>
          <button type="button" className="ghost-button ghost-button--accent" onClick={() => void playManually()}>
            再生する
          </button>
        </div>
      ) : null}

      {audioUrl && jobId ? (
        <a className="download-button" href={audioUrl} download={`oto_${jobId}.mp3`}>
          MP3 をダウンロード
        </a>
      ) : null}
    </section>
  );
}
