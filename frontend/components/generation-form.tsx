"use client";

import { useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
      setValidationError("プロンプトをご入力ください。");
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
    <form className="card-oto" onSubmit={handleSubmit}>
      <div>
        <p className="eyebrow">Generate</p>
        <h2>音楽を生成する</h2>
        <p className="card-lead" style={{ textAlign: "left", maxWidth: "none", marginTop: "6px" }}>
          思い描くサウンドの雰囲気を、自由な言葉でお伝えください。
        </p>
      </div>

      <div className="field">
        <Label htmlFor="prompt" className="field__label">
          プロンプト
        </Label>
        <Textarea
          id="prompt"
          name="prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="e.g. Calm lofi beats with rain sounds, warm and cozy, for deep focus"
          rows={5}
          maxLength={512}
          disabled={disabled}
          aria-describedby="prompt-help"
          required
          className="field__control field__control--textarea"
        />
        <span className="field__hint" id="prompt-help">
          生成中は、次のリクエストをお送りいただけません。
        </span>
      </div>

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
          詳細設定を{showAdvanced ? "隠す" : "表示"}
        </button>
      </div>

      {showAdvanced ? (
        <div className="advanced-grid">
          <div className="field">
            <Label htmlFor="bpm" className="field__label">
              BPM
            </Label>
            <Input
              id="bpm"
              type="number"
              inputMode="numeric"
              min={30}
              max={300}
              value={bpm}
              onChange={(event) => setBpm(event.target.value)}
              placeholder="Auto"
              disabled={disabled}
              className="field__control"
            />
          </div>

          <div className="field">
            <Label htmlFor="seed" className="field__label">
              Seed
            </Label>
            <Input
              id="seed"
              type="number"
              inputMode="numeric"
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              placeholder="Random"
              disabled={disabled}
              className="field__control"
            />
          </div>
        </div>
      ) : null}

      {validationError ? (
        <p className="inline-error" role="alert">
          {validationError}
        </p>
      ) : null}

      <button className="submit-button" type="submit" disabled={disabled || prompt.trim() === ""}>
        {disabled ? "生成中..." : "生成する"}
      </button>
    </form>
  );
}
