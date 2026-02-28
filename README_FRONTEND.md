# oto-factory フロントエンド設計・実装ガイド

## 概要

本書は `backend/` の FastAPI を利用する `frontend/` 実装の設計意図、現在の実装内容、起動方法、利用方法をまとめたものである。

現在のフロントエンドは Next.js App Router + TypeScript で実装済みであり、1 画面で以下を提供する。

- プロンプト入力とジョブ送信
- 進捗ポーリング
- 完了後の MP3 取得
- 自動再生の試行
- 手動再生フォールバック
- MP3 ダウンロード

前提は「1ページ完結」「1ジョブずつ操作」「認証なし」である。

---

## 実装済みディレクトリ構成

```text
frontend/
├── app/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── audio-player.tsx
│   ├── generation-form.tsx
│   ├── job-status-card.tsx
│   └── screen-shell.tsx
├── hooks/
│   ├── use-audio-playback.ts
│   └── use-generation-job.ts
├── lib/
│   ├── api.ts
│   ├── format.ts
│   └── types.ts
├── .env.example
├── eslint.config.mjs
├── next.config.ts
├── package.json
└── tsconfig.json
```

---

## 起動方法

```bash
cd /content/oto-factory/frontend
npm install
cp .env.example .env.local
```

`.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

開発サーバー起動:

```bash
npm run dev
```

検証:

```bash
npm run lint
npm run build
```

---

## 利用手順

1. backend を `http://localhost:8000` で起動する
2. frontend を `http://localhost:3000` で開く
3. 画面上部の `server` / `gpu` / `queue` を確認する
4. プロンプトを入力する
5. 長さを `30 / 60 / 120 / 180` 秒から選ぶ
6. 必要なら `詳細設定` で `BPM` と `Seed` を指定する
7. `生成を開始する` を押す
8. 進捗カードで状態を追う
9. 完了後、再生カードで音声を再生する
10. 必要なら `MP3 をダウンロード` を押す

---

## 採用方針

### フレームワーク

**Next.js（App Router, TypeScript）** を採用する。

理由は以下である。

- React ベースのフレームワークとして標準的である
- 将来的に SSR / 静的配信 / API プロキシの選択肢を持てる
- ルーティングとビルド設定を最小限で始められる
- MVP では 1 画面でも、将来の履歴画面や設定画面を追加しやすい

ただし、**MVP の主処理はクライアントサイドで完結**させる。
バックエンドはすでに CORS を許可しているため、まずはブラウザから `backend` を直接呼ぶ構成にする。

### 実装の原則

- 画面は 1 つに絞る
- グローバル状態管理ライブラリは導入しない
- `fetch` とカスタムフックで API 通信を閉じ込める
- UI ロジックは `status` にのみ依存し、`stage` は表示専用にする
- 生成中は送信ボタンを無効化し、1 クライアント 1 ジョブに制限する

---

## 機能要件

### 1. 生成フォーム

MVP では入力項目を最小化する。

- `prompt` は必須
- `duration` は初期値 `60` 秒で、UI はプリセット選択にする
- `bpm` と `seed` は「詳細設定」に退避し、初期表示では隠す

これにより、通常操作は「入力して送信する」だけに保つ。

### 2. ジョブ監視

送信成功後に `job_id` を保持し、`GET /api/jobs/{job_id}` をポーリングする。

- 表示に使う状態: `queued` / `running` / `completed` / `failed`
- `stage` はそのまま表示する
- `progress` がある場合はプログレスバーに反映する

### 3. 音声取得と再生

`completed` になったら `GET /api/jobs/{job_id}/audio` を呼び、MP3 を `Blob` として取得する。

- `Blob` から `Object URL` を作る
- `<audio>` にセットする
- `play()` を呼び、自動再生を試みる
- 同時にダウンロードボタンを有効化する

### 4. 失敗時の扱い

- `failed` の場合はエラーメッセージを表示する
- ユーザーは同じプロンプトで再送できる
- 送信ボタンは失敗後に再び有効化する

---

## API 連携

### 使用するエンドポイント

バックエンド実装に合わせて以下を使用する。

- `POST /api/generate`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/audio`
- `GET /api/health`

### 環境変数

フロントエンドでは以下を持つ。

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

MVP ではブラウザからこの URL に直接アクセスする。

### 型定義

`frontend/lib/types.ts` にバックエンドと揃えた型を持つ。

```ts
export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface GenerateRequest {
  prompt: string;
  duration: number;
  bpm?: number | null;
  seed?: number | null;
}

export interface GenerateJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number | null;
  stage: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}
```

---

## 状態設計

### フロントエンド状態

バックエンド状態とは別に、UI 都合の状態を持つ。

```text
idle
  -> submitting
  -> queued
  -> running
  -> downloading
  -> completed
  -> failed
```

### 状態遷移

1. `idle`
2. ユーザー送信で `submitting`
3. `POST /api/generate` 成功で `queued`
4. ポーリング結果が `running` なら `running`
5. ポーリング結果が `completed` なら `downloading`
6. 音声取得成功で `completed`
7. 途中のどこかで失敗したら `failed`

### 重要な制約

- 分岐条件は `status` のみを使う
- `stage` の文言には依存しない
- 1 ジョブ進行中は新規送信を受け付けない

---

## ポーリング設計

### 基本方針

- 送信後 2 秒間隔で `GET /api/jobs/{job_id}` を実行する
- `completed` または `failed` で停止する
- 通信中断や画面離脱に備えて `AbortController` を使う
- `GET /api/health` は初回表示時に 1 回実行し、アイドル時のみ 30 秒間隔で再取得する

### モバイル考慮

バッテリー消費を抑えるため、画面が非表示のときはポーリング頻度を落とす。

- `document.visibilityState === "visible"`: 2 秒
- それ以外: 5 秒

再表示時には即時再フェッチする。

### 409 対応

ごく短い競合で `audio` ダウンロードが `409` を返す可能性があるため、1 回だけ状態確認を挟んで再試行する。

### 実装修正メモ

- 同一 `job_id` への `audio` ダウンロードは 1 回だけに制限している
- React Strict Mode 下でも `downloading -> completed` が崩れないようにしている

---

## 音声再生設計

### 基本動作

`completed` 後に音声をダウンロードし、同じ `Blob` を再生と保存の両方に使う。

- 再生: `audio.src = objectUrl`
- 保存: `a.download = "oto_<job_id>.mp3"`

### 自動再生の扱い

モバイルブラウザ、とくに iOS Safari では、自動再生がブロックされることがある。
そのため実装は以下の方針にする。

- 送信ボタン押下時に `audio` 要素をユーザー操作に紐づけて初期化する
- 完了後に `play()` を試みる
- `play()` が拒否された場合は「再生」ボタンを強調表示し、手動再生へフォールバックする

つまり、**自動再生は必ず試みるが、手動再生の導線を必ず残す**。

### 音声要素

```html
<audio controls playsinline preload="metadata" />
```

`playsInline` を有効にし、モバイルで全画面プレーヤー遷移を避ける。

---

## 画面設計

### 画面構成

MVP はトップページ 1 画面で完結させる。

1. ヘッダー
2. プロンプト入力カード
3. 進捗カード
4. 再生カード

### モバイルファーストのレイアウト

- 基本は 1 カラム
- 幅いっぱいに使わず、読みやすい余白を確保する
- 送信ボタンは下部に大きく配置する
- 再生カードは完了後のみ表示する

### ブレークポイント

- `~767px`: 1 カラム固定、操作優先
- `768px~1023px`: 最大幅を広げるが構造は維持
- `1024px~`: フォームと状態カードの間隔を増やし、必要なら 2 カラムに拡張可能

MVP ではレイアウト構造を増やしすぎず、**見た目だけを段階的に広げる** 方針とする。

---

## ビジュアル方針

シンプルだが無機質にしない。作業音アプリとして、落ち着いたスタジオ感を持たせる。

- 背景: 暖色寄りの明るいグレー
- 文字: 濃いチャコール
- アクセント: 青緑または深いオレンジ
- カード: 角丸を抑えた面構成
- 影: 強すぎない薄いシャドウ

### タイポグラフィ

- 見出し: `Zen Kaku Gothic New`
- 本文/UI: `Noto Sans JP`

一般的なシステムフォント任せにせず、日本語での可読性を優先する。

### モーション

- 送信後に進捗カードをフェードイン
- 完了後に再生カードを短くスライド表示
- `prefers-reduced-motion` ではアニメーションを抑制する

---

## コンポーネント設計

### `app/page.tsx`

画面全体の組み立てのみを担当する。

- `ScreenShell`
- `GenerationForm`
- `JobStatusCard`
- `AudioPlayer`

### `components/generation-form.tsx`

責務は入力と送信である。

- `prompt` の入力
- `duration` の選択
- 詳細設定の開閉
- 送信中の UI 制御
- ホバー時のカーソル変更と押下フィードバック

### `components/job-status-card.tsx`

責務はジョブ状態の表示である。

- 状態バッジ
- `stage` テキスト
- プログレスバー
- エラー表示

### `components/audio-player.tsx`

責務は再生と保存である。

- `<audio>` の制御
- 自動再生の試行
- 手動再生フォールバック
- ダウンロードボタン

### `hooks/use-generation-job.ts`

責務はジョブ管理である。

- 生成開始
- ポーリング開始・停止
- `job_id` の保持
- UI 状態の集約

### `hooks/use-audio-playback.ts`

責務は音声取得と再生制御である。

- `Blob` ダウンロード
- `Object URL` の管理
- `play()` の試行
- 後始末

---

## エラーハンドリング

### ユーザーに見せるべきエラー

- 入力バリデーションエラー
- バックエンド未起動
- `503`: キュー満杯
- `404`: ジョブ期限切れまたは不正 ID
- `failed`: 生成失敗
- 自動再生失敗

### 表示方針

- 技術的な詳細はそのまま出しすぎず、操作可能な文言に変換する
- ただし `failed` 時の `error` は折りたたみで参照可能にする

例:

- 「サーバーに接続できない。バックエンドが起動しているか確認してほしい」
- 「現在キューが混雑している。少し待ってから再試行してほしい」
- 「生成は完了したが、ブラウザ制約で自動再生できなかった。再生ボタンを押してほしい」

---

## アクセシビリティ

- フォーム部品には明示的なラベルを付ける
- 状態変化は `aria-live="polite"` で通知する
- タップ領域は 44px 以上を確保する
- コントラスト比を十分に取る
- キーボード操作で送信・再生が可能であること

---

## MVP で実装しないもの

- ユーザー認証
- ジョブ履歴の永続化
- 複数ジョブの同時管理
- 波形表示
- 共有 URL
- バックエンドへのキャンセル要求
- オフライン再生

これらは後から追加できるが、初期段階では複雑さに対する効果が小さい。

---

## 実装順

1. `frontend/` を Next.js + TypeScript で初期化する
2. `lib/types.ts` と `lib/api.ts` を作り、API 契約を固定する
3. `use-generation-job.ts` で送信とポーリングを実装する
4. `use-audio-playback.ts` で MP3 ダウンロードと再生を実装する
5. 1 画面の UI を作る
6. モバイル幅で余白・ボタンサイズ・再生挙動を調整する

---

## 補足

本設計では、**フロントエンドはバックエンドの非同期ジョブモデルに忠実に従う**。
送信後の待機、状態取得、音声取得を明確に分離することで、実装が単純になり、将来的に履歴や通知を追加しやすくなる。

---

## 現在の実装との差分がない項目

以下は実装済みであり、本設計と一致している。

- 1 画面構成
- Next.js App Router + TypeScript
- モバイルファーストの 1 カラム中心レイアウト
- `status` 主導の UI 遷移
- 自動再生試行と手動再生フォールバック
- 完了後のダウンロード導線
