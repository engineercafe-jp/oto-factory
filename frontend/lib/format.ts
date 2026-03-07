import type { JobStatus, UiStatus } from "@/lib/types";

export function formatProgress(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return "0%";
  }

  return `${Math.round(value * 100)}%`;
}

export function mapStatusLabel(status: UiStatus | JobStatus): string {
  switch (status) {
    case "idle":
      return "待機中";
    case "submitting":
      return "送信中";
    case "queued":
      return "処理待ち";
    case "running":
      return "生成中";
    case "downloading":
      return "音声準備中";
    case "completed":
      return "完了";
    case "failed":
      return "エラー";
    default:
      return status;
  }
}

export function formatTimestamp(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
