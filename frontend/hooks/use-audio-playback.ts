"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, downloadAudio, getJobStatus } from "@/lib/api";

interface AudioState {
  audioUrl: string | null;
  autoplayBlocked: boolean;
  loading: boolean;
  error: string | null;
}

const INITIAL_AUDIO_STATE: AudioState = {
  audioUrl: null,
  autoplayBlocked: false,
  loading: false,
  error: null,
};

export function useAudioPlayback() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const [state, setState] = useState<AudioState>(INITIAL_AUDIO_STATE);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }
    };
  }, []);

  const primeForPlayback = () => {
    const element = audioRef.current;
    if (!element) {
      return;
    }

    element.muted = true;
    const playAttempt = element.play();
    if (playAttempt) {
      void playAttempt.catch(() => undefined).finally(() => {
        element.pause();
        element.currentTime = 0;
        element.muted = false;
      });
    } else {
      element.muted = false;
    }
  };

  const attachAudioRef = (node: HTMLAudioElement | null) => {
    audioRef.current = node;
  };

  const loadAudio = async (jobId: string): Promise<{ ok: true } | { ok: false; error: string }> => {
    setState((current) => ({
      ...current,
      loading: true,
      error: null,
      autoplayBlocked: false,
    }));

    try {
      let blob: Blob;
      try {
        blob = await downloadAudio(jobId);
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          await getJobStatus(jobId);
          blob = await downloadAudio(jobId);
        } else {
          throw error;
        }
      }

      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
      }

      const url = URL.createObjectURL(blob);
      objectUrlRef.current = url;
      const element = audioRef.current;

      if (element) {
        element.src = url;
        element.load();
      }

      setState({
        audioUrl: url,
        autoplayBlocked: false,
        loading: false,
        error: null,
      });

      if (element) {
        try {
          await element.play();
        } catch {
          setState((current) => ({
            ...current,
            autoplayBlocked: true,
          }));
        }
      }

      return { ok: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : "音声取得に失敗した";
      setState({
        ...INITIAL_AUDIO_STATE,
        error: message,
      });
      return { ok: false, error: message };
    }
  };

  const playManually = async () => {
    const element = audioRef.current;
    if (!element) {
      return;
    }

    try {
      await element.play();
      setState((current) => ({
        ...current,
        autoplayBlocked: false,
      }));
    } catch {
      setState((current) => ({
        ...current,
        autoplayBlocked: true,
      }));
    }
  };

  return {
    ...state,
    audioRef,
    attachAudioRef,
    primeForPlayback,
    loadAudio,
    playManually,
  };
}
