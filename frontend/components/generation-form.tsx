"use client";

import { useState } from "react";

import type { GenerateRequest } from "@/lib/types";

const DURATION_PRESETS = [30, 60, 120, 180];

interface GenerationFormProps {
  disabled: boolean;
  onSubmit: (payload: GenerateRequest) => Promise<void> | void;
  onPrimePlayback: () => void;
}

export function GenerationForm({
  disabled,
  onSubmit,
  onPrimePlayback,
}: GenerationFormProps) {
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(60);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [bpm, setBpm] = useState("");
  const [seed, setSeed] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedPrompt = prompt.trim();

    if (!trimmedPrompt) {
      setValidationError("プロンプトを入力してほしい。");
      return;
    }

    setValidationError(null);
    onPrimePlayback();

    await onSubmit({
      prompt: trimmedPrompt,
      duration,
      bpm: bpm === "" ? null : Number(bpm),
      seed: seed === "" ? null : Number(seed),
    });
  };

  return (
    <form className="card stack" onSubmit={handleSubmit}>
      <div className="card__header">
        <div>
          <p className="eyebrow">Generate</p>
          <h2>音の指示を送る</h2>
        </div>
        <p className="card__lead">短い説明でも構わない。作りたい空気感をそのまま書く。</p>
      </div>

      <label className="field">
        <span className="field__label">プロンプト</span>
        <textarea
          className="field__control field__control--textarea"
          name="prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="例: 雨音の奥で静かに鳴るローファイ、集中用、暖かい質感"
          rows={5}
          maxLength={512}
          disabled={disabled}
          aria-describedby="prompt-help"
          required
        />
        <span className="field__hint" id="prompt-help">
          1 つのジョブが終わるまでは次を送れない。
        </span>
      </label>

      <fieldset className="field-group">
        <legend className="field__label">長さ</legend>
        <div className="pill-group" role="radiogroup" aria-label="duration presets">
          {DURATION_PRESETS.map((preset) => (
            <label className="pill-option" key={preset}>
              <input
                type="radio"
                name="duration"
                value={preset}
                checked={duration === preset}
                onChange={() => setDuration(preset)}
                disabled={disabled}
              />
              <span>{preset}秒</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="details-toggle">
        <button
          type="button"
          className="ghost-button"
          onClick={() => setShowAdvanced((current) => !current)}
          aria-expanded={showAdvanced}
        >
          詳細設定 {showAdvanced ? "を閉じる" : "を開く"}
        </button>
      </div>

      {showAdvanced ? (
        <div className="advanced-grid">
          <label className="field">
            <span className="field__label">BPM</span>
            <input
              className="field__control"
              type="number"
              inputMode="numeric"
              min={30}
              max={300}
              value={bpm}
              onChange={(event) => setBpm(event.target.value)}
              placeholder="自動"
              disabled={disabled}
            />
          </label>

          <label className="field">
            <span className="field__label">Seed</span>
            <input
              className="field__control"
              type="number"
              inputMode="numeric"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              placeholder="ランダム"
              disabled={disabled}
            />
          </label>
        </div>
      ) : null}

      {validationError ? (
        <p className="inline-error" role="alert">
          {validationError}
        </p>
      ) : null}

      <button className="submit-button" type="submit" disabled={disabled}>
        {disabled ? "処理中..." : "生成を開始する"}
      </button>
    </form>
  );
}
