"use client";

import { useCallback, useRef, useState } from "react";

import { downloadAudio, generateMusic, getJobStatus } from "@/lib/api";
import type { GenerateRequest, LoopStatus, UiError } from "@/lib/types";

/** ループ生成の内部状態 */
interface LoopState {
  loopStatus: LoopStatus;
  nextStatus: "idle" | "generating" | "ready" | "failed";
  waitingForNext: boolean;
  error: UiError | null;
  message: string | null;
}

const INITIAL_STATE: LoopState = {
  loopStatus: "inactive",
  nextStatus: "idle",
  waitingForNext: false,
  error: null,
  message: null,
};

/** ポーリング間隔（ms） */
const POLL_INTERVAL = 2000;

/** 生成時間の初期推定（ms） */
const DEFAULT_GEN_TIME = 45000;

/** 生成時間のマージン倍率 */
const GEN_TIME_MARGIN = 1.3;

/** 次トラックの先行生成に加えるバッファ（秒） */
const TRIGGER_BUFFER_SEC = 15;

/** AudioPlayback フックの公開 API のうちループで使う部分 */
interface AudioPlaybackHandle {
  audioRef: React.RefObject<HTMLAudioElement | null>;
  loadFromBlob: (blob: Blob) => Promise<{ ok: true } | { ok: false; error: string }>;
}

/**
 * ループ生成フック。
 * 再生中の曲が終わる前に次の曲を生成・ダウンロードし、シームレスに連続再生する。
 */
export function useLoopGeneration() {
  const [state, setState] = useState<LoopState>(INITIAL_STATE);

  // 内部 ref
  const abortRef = useRef<AbortController | null>(null);
  const nextBlobRef = useRef<Blob | null>(null);
  const audioHandleRef = useRef<AudioPlaybackHandle | null>(null);
  const getPayloadRef = useRef<(() => GenerateRequest) | null>(null);
  const genHistoryRef = useRef<number[]>([]);
  const timeupdateCleanupRef = useRef<(() => void) | null>(null);
  const triggerFiredRef = useRef(false);
  const loopStatusRef = useRef<LoopStatus>("inactive");

  /** loopStatus を state と ref に同時にセットする */
  const setLoopStatus = useCallback((status: LoopStatus) => {
    loopStatusRef.current = status;
    setState((c) => ({ ...c, loopStatus: status }));
  }, []);

  /** 生成時間の推定値（ms）を返す */
  const estimateGenTime = useCallback((): number => {
    const history = genHistoryRef.current;
    if (history.length === 0) return DEFAULT_GEN_TIME;
    const max = Math.max(...history);
    return max * GEN_TIME_MARGIN;
  }, []);

  /** 1 トラック分の生成→ダウンロードを実行し Blob を返す */
  const generateAndDownload = useCallback(
    async (payload: GenerateRequest, signal: AbortSignal): Promise<Blob> => {
      // 1. POST /api/generate
      const { job_id } = await generateMusic(payload, signal);

      // 2. ポーリングで完了を待つ
      // eslint-disable-next-line no-constant-condition
      while (true) {
        await new Promise((r) => setTimeout(r, POLL_INTERVAL));
        if (signal.aborted) throw new DOMException("Aborted", "AbortError");

        const job = await getJobStatus(job_id, signal);
        if (job.status === "completed") break;
        if (job.status === "failed") {
          throw new Error(job.error ?? "生成に失敗した");
        }
      }

      // 3. 音声ダウンロード
      return downloadAudio(job_id, signal);
    },
    [],
  );

  /** timeupdate リスナーを設置し、トリガーポイントで次トラック生成を開始する */
  const setupTimeupdateListener = useCallback(
    (audioElement: HTMLAudioElement) => {
      // 前回のリスナーをクリーンアップ
      timeupdateCleanupRef.current?.();
      triggerFiredRef.current = false;

      const handler = () => {
        if (triggerFiredRef.current) return;
        if (loopStatusRef.current !== "active") return;

        const { currentTime, duration } = audioElement;
        if (!duration || !isFinite(duration)) return;

        const estGen = estimateGenTime() / 1000; // 秒に変換
        const triggerPoint = duration - estGen - TRIGGER_BUFFER_SEC;

        // triggerPoint が 0 以下なら即座に生成開始
        if (currentTime >= triggerPoint || triggerPoint <= 0) {
          triggerFiredRef.current = true;
          void startNextGeneration();
        }
      };

      audioElement.addEventListener("timeupdate", handler);
      timeupdateCleanupRef.current = () => {
        audioElement.removeEventListener("timeupdate", handler);
      };
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  /** 次のトラックを生成する内部関数 */
  const startNextGeneration = useCallback(async () => {
    const getPayload = getPayloadRef.current;
    if (!getPayload) return;

    setState((c) => ({ ...c, nextStatus: "generating" }));

    const controller = new AbortController();
    abortRef.current = controller;

    const startTime = Date.now();
    try {
      const payload = getPayload();
      const blob = await generateAndDownload(payload, controller.signal);

      if (controller.signal.aborted) return;

      // 生成時間を記録（直近 3 回）
      const elapsed = Date.now() - startTime;
      genHistoryRef.current = [...genHistoryRef.current.slice(-2), elapsed];

      nextBlobRef.current = blob;
      setState((c) => {
        // waitingForNext が true なら、曲が既に終わっている → 即座に再生
        if (c.waitingForNext) {
          void playNextTrack();
          return { ...c, nextStatus: "ready" };
        }
        return { ...c, nextStatus: "ready" };
      });
    } catch (error) {
      if (controller.signal.aborted) return;

      const detail = error instanceof Error ? error.message : "次のトラックの生成に失敗した";
      setState((c) => ({
        ...c,
        nextStatus: "failed",
        error: { summary: "次のトラックの生成に失敗しました。", detail },
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generateAndDownload]);

  /** nextBlob を再生に切り替え、次の生成サイクルを準備する */
  const playNextTrack = useCallback(async () => {
    const handle = audioHandleRef.current;
    const blob = nextBlobRef.current;
    if (!handle || !blob) return;

    nextBlobRef.current = null;
    setState((c) => ({ ...c, nextStatus: "idle", waitingForNext: false }));

    const result = await handle.loadFromBlob(blob);
    if (!result.ok) {
      setLoopStatus("inactive");
      setState((c) => ({
        ...c,
        loopStatus: "inactive",
        error: { summary: "音声の再生に失敗しました。", detail: result.error },
      }));
      return;
    }

    // 新しいトラックの timeupdate 監視を開始
    const element = handle.audioRef.current;
    if (element) {
      setupTimeupdateListener(element);
    }
  }, [setLoopStatus, setupTimeupdateListener]);

  /** ループ開始 */
  const startLoop = useCallback(
    async (
      payload: GenerateRequest,
      audioPlayback: AudioPlaybackHandle,
      getPayload: () => GenerateRequest,
    ) => {
      // 既にアクティブなら何もしない
      if (loopStatusRef.current !== "inactive") return;

      audioHandleRef.current = audioPlayback;
      getPayloadRef.current = getPayload;
      setLoopStatus("active");
      setState((c) => ({
        ...c,
        loopStatus: "active",
        nextStatus: "idle",
        waitingForNext: false,
        error: null,
        message: null,
      }));

      // 第 1 トラックを生成
      const controller = new AbortController();
      abortRef.current = controller;

      const startTime = Date.now();
      try {
        const blob = await generateAndDownload(payload, controller.signal);
        if (controller.signal.aborted) return;

        // 生成時間を記録
        const elapsed = Date.now() - startTime;
        genHistoryRef.current = [elapsed];

        // 再生開始
        const result = await audioPlayback.loadFromBlob(blob);
        if (!result.ok) {
          setLoopStatus("inactive");
          setState((c) => ({
            ...c,
            loopStatus: "inactive",
            error: { summary: "音声の再生に失敗しました。", detail: result.error },
          }));
          return;
        }

        // timeupdate 監視を開始
        const element = audioPlayback.audioRef.current;
        if (element) {
          setupTimeupdateListener(element);
        }
      } catch (error) {
        if (controller.signal.aborted) return;

        const detail = error instanceof Error ? error.message : "生成に失敗した";
        setLoopStatus("inactive");
        setState((c) => ({
          ...c,
          loopStatus: "inactive",
          error: { summary: "最初のトラックの生成に失敗しました。", detail },
        }));
      }
    },
    [generateAndDownload, setLoopStatus, setupTimeupdateListener],
  );

  /** ループ停止 */
  const stopLoop = useCallback(() => {
    setLoopStatus("stopping");
    // 生成中のリクエストを abort
    abortRef.current?.abort();
    abortRef.current = null;
    nextBlobRef.current = null;
    timeupdateCleanupRef.current?.();
    setState((c) => ({ ...c, nextStatus: "idle", waitingForNext: false }));
  }, [setLoopStatus]);

  /** <audio> の onended から呼ばれる */
  const onTrackEnded = useCallback(() => {
    const status = loopStatusRef.current;

    if (status === "stopping") {
      // ループ終了
      setLoopStatus("inactive");
      timeupdateCleanupRef.current?.();
      setState((c) => ({
        ...c,
        loopStatus: "inactive",
        nextStatus: "idle",
        waitingForNext: false,
        message: null,
      }));
      return;
    }

    // nextStatus を取得するため setState の関数形式を使用
    setState((c) => {
      if (c.nextStatus === "ready") {
        void playNextTrack();
        return c;
      }

      if (c.nextStatus === "generating") {
        return { ...c, waitingForNext: true };
      }

      if (c.nextStatus === "failed") {
        loopStatusRef.current = "inactive";
        return {
          ...c,
          loopStatus: "inactive",
          waitingForNext: false,
          error: c.error ?? { summary: "次のトラックの生成に失敗したため、ループを停止しました。" },
        };
      }

      // nextStatus === "idle": 生成がまだ始まっていない（曲が短い場合）
      // → 即座に次の生成を開始し、待機状態にする
      triggerFiredRef.current = true;
      void startNextGeneration();
      return { ...c, waitingForNext: true };
    });
  }, [playNextTrack, setLoopStatus, startNextGeneration]);

  return {
    loopStatus: state.loopStatus,
    nextTrackReady: state.nextStatus === "ready",
    waitingForNext: state.waitingForNext,
    error: state.error,
    message: state.message,
    startLoop,
    stopLoop,
    onTrackEnded,
  };
}
