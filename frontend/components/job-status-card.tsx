import { formatProgress, formatTimestamp, mapStatusLabel } from "@/lib/format";
import type { JobStatusResponse, UiError, UiStatus } from "@/lib/types";

interface JobStatusCardProps {
  uiStatus: UiStatus;
  job: JobStatusResponse | null;
  message: string | null;
  error: UiError | null;
}

export function JobStatusCard({ uiStatus, job, message, error }: JobStatusCardProps) {
  const progress = job?.progress ?? (uiStatus === "completed" ? 1 : 0);
  const createdAt = formatTimestamp(job?.created_at ?? null);
  const completedAt = formatTimestamp(job?.completed_at ?? null);

  return (
    <section className="card-oto reveal-card" aria-live="polite">
      <div className="card-header-row">
        <div>
          <p className="eyebrow">Status</p>
          <h2>生成ステータス</h2>
        </div>
        <span className={`status-badge status-badge--${uiStatus}`}>{mapStatusLabel(uiStatus)}</span>
      </div>

      <div className="status-meta">
        <div>
          <span className="status-meta__label">job id</span>
          <strong>{job?.job_id ?? "—"}</strong>
        </div>
        <div>
          <span className="status-meta__label">stage</span>
          <strong>{job?.stage ?? message ?? "リクエストをお待ちしています"}</strong>
        </div>
      </div>

      <div className="progress-block" aria-label={`progress ${formatProgress(progress)}`}>
        <div className="progress-block__track">
          <div className="progress-block__bar" style={{ width: `${Math.max(progress, 0) * 100}%` }} />
        </div>
        <span>{formatProgress(progress)}</span>
      </div>

      <div className="timestamp-row">
        <span>受付 {createdAt ?? "-"}</span>
        <span>完了 {completedAt ?? "-"}</span>
      </div>

      {error ? (
        <div className="error-panel" role="alert">
          <strong>{error.summary}</strong>
          {error.detail ? (
            <details>
              <summary>詳細を表示</summary>
              <p>{error.detail}</p>
            </details>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
