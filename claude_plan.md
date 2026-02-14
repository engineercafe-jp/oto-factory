# ACE-Step 1.5 検証環境構築プラン

## 現在の環境分析

### ハードウェア・ソフトウェア構成

```
- 環境: Google Colab
- OS: Ubuntu 22.04.5 LTS
- GPU: NVIDIA A100-SXM4-80GB (80GB VRAM)
- CUDA: 12.8
- Python (システム): 3.12.12
- uv: 0.10.0 (インストール済み)
- ディスク空き容量: 192GB
```

### ACE-Step 1.5 の要件

```
- Python: 3.11.* (厳格な要件)
- GPU: CUDA GPU 推奨
- VRAM: DiTのみ≥4GB、LLM+DiT≥6GB
- ディスク: コアモデルに約10GB
```

### 互換性チェック

| 項目 | 要件 | 現在の環境 | 状態 |
|------|------|-----------|------|
| GPU | CUDA GPU | A100 80GB | ✅ 十分 |
| VRAM | ≥6GB | 80GB | ✅ 最高スペック |
| CUDA | 対応 | 12.8 | ✅ 対応 |
| Python | 3.11.* | 3.12.12 | ⚠️ バージョン不一致 |
| ディスク | ~10GB | 192GB | ✅ 十分 |

## 環境構築方法の比較

### Option A: uv使用（推奨）⭐

**概要:**
ACE-Step 1.5 の公式推奨方法である。uv が Python 3.11.14 を自動的にダウンロード・管理し、完全に隔離された環境を構築する。

**メリット:**
- ✅ 公式の推奨方法で最も信頼性が高い
- ✅ Python 3.11 を自動でダウンロード・管理（システムPythonに影響なし）
- ✅ 依存関係の完全な隔離（他のプロジェクトと競合しない）
- ✅ `pyproject.toml` による厳密なバージョン管理
- ✅ 高速なパッケージインストール
- ✅ 再現性が高い（同じ環境を簡単に再構築可能）
- ✅ CUDA 12.8 対応の PyTorch を自動選択

**デメリット:**
- ❌ Colab環境では若干の追加設定が必要
- ❌ uvの学習コストがある（ただし使い方は単純）

**セットアップ手順:**

```bash
# 1. プロジェクトディレクトリに移動
cd /content/oto-factory/ACE-Step-1.5

# 2. Python 3.11 をインストール・ピン留め（完了済み）
uv python install 3.11
uv python pin 3.11

# 3. 依存関係をインストール
uv sync

# 4. Gradio UI を起動
uv run acestep --language ja --server-name 0.0.0.0

# または REST API サーバーを起動
uv run acestep-api --host 0.0.0.0
```

**推奨設定（A100 80GB環境）:**

```bash
# 最高品質構成
uv run acestep \
  --language ja \
  --server-name 0.0.0.0 \
  --lm_model_path acestep-5Hz-lm-4B \
  --config_path acestep-v15-turbo \
  --init_service true
```

### Option B: pip使用（非推奨）

**概要:**
Colab のシステム Python (3.12.12) を使用して pip でインストールする方法。

**メリット:**
- ✅ シンプルで理解しやすい
- ✅ Colabの標準的な方法

**デメリット:**
- ❌ Python 3.12 は公式にサポートされていない（`requires-python = "==3.11.*"`）
- ❌ pyproject.toml を手動で修正する必要がある
- ❌ 依存関係の競合リスクが高い
- ❌ 再現性が低い
- ❌ 予期しないバージョンの PyTorch がインストールされる可能性
- ❌ 公式サポート外のため問題が発生しやすい

**結論:** Python バージョンの不一致により、この方法は推奨しない。

## 推奨プラン: Option A (uv使用)

### 理由

1. **公式推奨:** ACE-Step 1.5 の README とドキュメントで推奨されている標準的な方法である
2. **Python バージョン問題の解決:** uv が Python 3.11.14 を自動管理するため、バージョン不一致の問題が発生しない
3. **環境隔離:** システム環境を汚染せず、クリーンな状態を保つ
4. **A100 最適化:** 80GB VRAM を最大限活用できる設定が可能
5. **再現性:** 他の環境でも同じ構成を簡単に再現できる

### 具体的な実装ステップ

## 🚀 実践: Gradio UI 起動までの完全ガイド

以下は、Option A（uv使用）で Gradio UI を起動するまでの実際の手順である。

### 事前準備チェックリスト

- [x] Google Colab 環境である
- [x] GPU ランタイムが有効である（A100）
- [x] `/content/oto-factory` ディレクトリが存在する
- [x] `ACE-Step-1.5` サブモジュールが初期化されている
- [x] uv がインストールされている（0.10.0）
- [x] Python 3.11.14 がインストールされている
- [x] `.python-version` に `3.11` が設定されている

### 実行フロー全体（所要時間: 約15-20分）

```
Step 1: 環境確認 (1分)
  ↓
Step 2: 依存関係インストール (5-10分) ← 最も時間がかかる
  ↓
Step 3: 環境検証 (1分)
  ↓
Step 4: モデルダウンロード (起動時自動、初回のみ5-10分)
  ↓
Step 5: Gradio UI 起動 (1-2分)
  ↓
Step 6: アクセスと動作確認 (1分)
```

---

### Step 1: 環境確認（所要時間: 1分）

まず、現在の環境を確認する。

```bash
# プロジェクトディレクトリに移動
cd /content/oto-factory/ACE-Step-1.5

# 現在地を確認
pwd
# 期待される出力: /content/oto-factory/ACE-Step-1.5

# Python 3.11 がピン留めされていることを確認
cat .python-version
# 期待される出力: 3.11

# uv のバージョン確認
uv --version
# 期待される出力: uv 0.10.0 (または類似のバージョン)

# GPU 確認
nvidia-smi --query-gpu=name,memory.total --format=csv
# 期待される出力: name, memory.total [MiB]
#                 NVIDIA A100-SXM4-80GB, 81920 MiB

# CUDA バージョン確認
nvcc --version | grep "release"
# 期待される出力: Cuda compilation tools, release 12.8, ...
```

**✅ チェックポイント:**
- すべてのコマンドが期待通りの出力を返すこと
- エラーが表示されないこと

---

### Step 2: 依存関係インストール（所要時間: 5-10分）⏱️

最も時間がかかるステップである。uv が Python 3.11.14 の仮想環境を作成し、すべての依存関係をインストールする。

```bash
# ACE-Step-1.5 ディレクトリにいることを確認
cd /content/oto-factory/ACE-Step-1.5

# 依存関係のインストール
uv sync
```

**実行中の出力例:**
```
Resolved 150 packages in 2.5s
Downloaded 150 packages in 45.3s
Installing...
  ✓ torch==2.10.0+cu128
  ✓ transformers==4.57.0
  ✓ diffusers==0.32.0
  ✓ gradio==6.2.0
  ✓ accelerate==1.12.0
  ...
  ✓ nano-vllm (from path)
Installed 150 packages in 5m 23s
```

**期待される結果:**
- ✅ Python 3.11.14 の仮想環境が `.venv` ディレクトリに作成される
- ✅ PyTorch 2.10.0+cu128 (CUDA 12.8対応) がインストールされる
- ✅ transformers, diffusers, gradio などの主要依存関係がインストールされる
- ✅ nano-vllm (ローカルパッケージ) がインストールされる
- ✅ 合計150個前後のパッケージがインストールされる

**⚠️ 注意:**
- 初回実行時は PyTorch など大きなパッケージをダウンロードするため、5-10分かかる
- ネットワーク速度によってはさらに時間がかかる場合がある
- エラーが出た場合は、次のステップに進む前に解決すること

**トラブルシューティング:**
```bash
# もしエラーが出た場合、キャッシュをクリアして再試行
uv cache clean
uv sync

# または、詳細なログを確認
uv sync --verbose
```

---

### Step 3: 環境検証（所要時間: 1分）

インストールが成功したか検証する。

```bash
# Python のバージョンを確認（仮想環境内）
uv run python --version
# 期待される出力: Python 3.11.14

# PyTorch がインストールされているか確認
uv run python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
# 期待される出力: PyTorch version: 2.10.0+cu128

# CUDA が PyTorch で認識されているか確認
uv run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
# 期待される出力: CUDA available: True

# GPU デバイス名を確認
uv run python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"Not found\"}')"
# 期待される出力: GPU: NVIDIA A100-SXM4-80GB

# Gradio がインストールされているか確認
uv run python -c "import gradio; print(f'Gradio version: {gradio.__version__}')"
# 期待される出力: Gradio version: 6.2.0

# ACE-Step パッケージが認識されているか確認
uv run python -c "import acestep; print('ACE-Step package loaded successfully')"
# 期待される出力: ACE-Step package loaded successfully
```

**✅ チェックポイント:**
- すべてのインポートが成功すること
- CUDA が `True` であること
- GPU が正しく認識されていること

**❌ もしエラーが出た場合:**
```bash
# 依存関係を再インストール
uv sync --reinstall

# または、特定のパッケージを再インストール
uv pip install --reinstall torch torchvision torchaudio
```

---

### Step 4: モデルダウンロード（初回起動時自動）

モデルは初回起動時に自動的にダウンロードされる。または、事前にダウンロードすることも可能である。

**Option A: 起動時に自動ダウンロード（推奨）**

次のステップ（Step 5）で Gradio UI を起動すると、自動的にモデルがダウンロードされる。
初回起動時のみ追加で 5-10分かかる。

**Option B: 事前にダウンロード**

起動前にモデルを事前ダウンロードしたい場合は、以下を実行する。

```bash
# ダウンロード可能なモデルの一覧を表示
uv run acestep-download --list

# メインモデルをダウンロード（VAE, DiT, LM 1.7B など）
uv run acestep-download

# 追加で 4B LM モデルをダウンロード（A100 向け高品質モデル）
uv run acestep-download --model acestep-5Hz-lm-4B

# または ModelScope から（場合によっては高速）
uv run acestep-download --download-source modelscope
```

**ダウンロードされるモデル（合計 10-15GB）:**
- `vae`: 音声エンコーダー/デコーダー (~500MB)
- `Qwen3-Embedding-0.6B`: テキストエンベディング (~1.2GB)
- `acestep-v15-turbo`: DiT モデル（デフォルト）(~3GB)
- `acestep-5Hz-lm-1.7B`: LM モデル（デフォルト）(~3.5GB)
- `acestep-5Hz-lm-4B`: LM モデル（A100用）(~8GB)

**保存場所:**
```bash
# モデルは以下のディレクトリに保存される
ls -lh checkpoints/
# または
ls -lh ~/.cache/huggingface/hub/
```

---

### Step 5: Gradio UI 起動（所要時間: 1-2分 + 初回モデルロード）⏱️

いよいよ Gradio UI を起動する。

#### 5-1: 基本的な起動（まずはこれを試す）

```bash
# ACE-Step-1.5 ディレクトリにいることを確認
cd /content/oto-factory/ACE-Step-1.5

# Gradio UI を起動（日本語、外部アクセス許可）
uv run acestep --language ja --server-name 0.0.0.0
```

#### 5-2: A100 向け最適化起動（推奨）

A100 80GB の性能を最大限活用する設定：

```bash
uv run acestep \
  --language ja \
  --server-name 0.0.0.0 \
  --port 7860 \
  --lm_model_path acestep-5Hz-lm-4B \
  --config_path acestep-v15-turbo \
  --init_service true \
  --backend vllm
```

**パラメータ説明:**
- `--language ja`: UI を日本語で表示
- `--server-name 0.0.0.0`: 外部からアクセス可能にする（Colab で必須）
- `--port 7860`: ポート番号（デフォルト）
- `--lm_model_path acestep-5Hz-lm-4B`: 最高品質の 4B LM モデルを使用
- `--config_path acestep-v15-turbo`: 高速な Turbo DiT モデルを使用
- `--init_service true`: 起動時にモデルを事前ロード（初回アクセスが高速になる）
- `--backend vllm`: vLLM バックエンドで高速推論

**起動中の出力例:**

```
2026-02-14 08:00:00,123 | INFO | acestep.gpu_config | Detected GPU: NVIDIA A100-SXM4-80GB (80GB VRAM)
2026-02-14 08:00:00,234 | INFO | acestep.gpu_config | GPU Tier: 5 (≥24GB) - Enabling full features
2026-02-14 08:00:01,345 | INFO | acestep.llm_inference | Initializing LM model: acestep-5Hz-lm-4B
2026-02-14 08:00:01,456 | INFO | acestep.llm_inference | Backend: vllm
2026-02-14 08:00:15,678 | INFO | acestep.handler | Loading DiT model: acestep-v15-turbo
2026-02-14 08:00:25,890 | INFO | acestep.handler | Loading VAE model
2026-02-14 08:00:30,123 | INFO | acestep.acestep_v15_pipeline | All models loaded successfully
2026-02-14 08:00:30,234 | INFO | gradio.server | Running on local URL:  http://0.0.0.0:7860
2026-02-14 08:00:30,345 | INFO | gradio.server | Running on public URL: https://xxxxx.gradio.live
```

**✅ チェックポイント:**
- `Running on local URL:  http://0.0.0.0:7860` が表示される
- エラーメッセージが表示されない
- GPU が正しく認識されている（ログに表示される）
- モデルがすべて正常にロードされている

**⚠️ Colab 固有の注意:**
- Gradio は自動的に公開 URL を生成する（`https://xxxxx.gradio.live` の形式）
- または Colab のポートフォワーディング機能で `https://xxx-7860.proxy.runpod.net/` のような URL が表示される
- この URL をクリックしてアクセスする

**起動が完了すると:**
- Colab のセル出力に URL が表示される
- その URL をクリックすると Gradio UI が開く

---

### Step 6: アクセスと動作確認（所要時間: 1分）

#### 6-1: UI アクセス

起動時に表示された URL（例: `https://xxxxx.gradio.live`）をクリックして、ブラウザで開く。

**期待される画面:**
- Gradio UI が日本語で表示される
- 複数のタブが表示される:
  - 🎵 音楽生成
  - 🎨 Cover 生成
  - ✂️ Repaint & 編集
  - 🎤 Vocal2BGM
  - 📊 結果
  - 🎓 LoRA トレーニング

#### 6-2: サービス状態の確認

UI 上部に「サービス状態」が表示される。

**正常な状態:**
```
✅ DiT Model: Loaded (acestep-v15-turbo)
✅ LM Model: Loaded (acestep-5Hz-lm-4B)
✅ VAE: Loaded
✅ GPU: NVIDIA A100-SXM4-80GB (80GB VRAM)
```

#### 6-3: 簡単な生成テスト

最初の音楽を生成してみる。

1. **「🎵 音楽生成」タブを開く**

2. **Simple Mode を選択**

3. **プロンプトを入力:**
   ```
   穏やかなピアノのインストゥルメンタル、リラックスできる雰囲気
   ```

4. **設定:**
   - Duration: `30` 秒（最初は短めに）
   - Generate を クリック

5. **生成を待つ:**
   - A100 では 30秒の楽曲が数秒で生成されるはず
   - 進捗バーが表示される

6. **結果を確認:**
   - 生成された音声ファイルが表示される
   - 再生ボタンで音楽を聴く
   - ダウンロード可能

**✅ 成功の確認:**
- 音楽が正常に生成される
- 音声ファイルが再生できる
- エラーが表示されない
- 生成速度が高速である（A100 なら数秒）

---

### GPU 使用状況の確認

別のターミナル（または Colab の別のセル）で GPU 使用状況を確認する。

```bash
# GPU メモリ使用量をリアルタイム監視
watch -n 1 nvidia-smi

# または1回だけ確認
nvidia-smi
```

**期待される VRAM 使用量（4B LM モデル使用時）:**
- アイドル時: 約 20-30GB
- 生成中: 約 30-40GB
- 80GB の VRAM に対して余裕がある状態

---

### 🎉 完了！

Gradio UI が正常に起動し、音楽生成が成功したら環境構築は完了である。

**次にできること:**
1. 様々なプロンプトで音楽を生成してみる
2. Cover 生成、Repaint、Vocal2BGM などの高度な機能を試す
3. 長時間の楽曲（最大10分）を生成してみる
4. バッチ生成で複数の楽曲を同時生成
5. LoRA トレーニングで独自のスタイルを学習

---

### トラブルシューティング（起動時）

#### エラー: `ModuleNotFoundError: No module named 'torch'`

```bash
# 依存関係を再インストール
cd /content/oto-factory/ACE-Step-1.5
uv sync --reinstall
```

#### エラー: `CUDA out of memory`

```bash
# より小さい LM モデルに切り替え
uv run acestep --lm_model_path acestep-5Hz-lm-1.7B

# または LM を無効化
uv run acestep --init_llm false
```

#### エラー: `Address already in use (port 7860)`

```bash
# 別のポートを使用
uv run acestep --port 7861
```

#### Gradio UI にアクセスできない

```bash
# --share オプションで公開 URL を生成
uv run acestep --language ja --server-name 0.0.0.0 --share
```

#### モデルダウンロードが遅い、または失敗する

```bash
# ModelScope を使用（中国のサーバー）
uv run acestep --download-source modelscope

# または事前に手動ダウンロード
uv run acestep-download --download-source modelscope
```

---

### クイックリファレンス

環境構築後によく使うコマンドをまとめた。

#### 基本的な起動

```bash
# シンプルな起動
cd /content/oto-factory/ACE-Step-1.5
uv run acestep --language ja --server-name 0.0.0.0

# A100 最適化起動（推奨）
uv run acestep \
  --language ja \
  --server-name 0.0.0.0 \
  --lm_model_path acestep-5Hz-lm-4B \
  --config_path acestep-v15-turbo \
  --init_service true \
  --backend vllm
```

#### モデル管理

```bash
# モデル一覧
uv run acestep-download --list

# メインモデルダウンロード
uv run acestep-download

# 特定モデルダウンロード
uv run acestep-download --model acestep-5Hz-lm-4B

# ModelScope から
uv run acestep-download --download-source modelscope
```

#### 環境管理

```bash
# Python バージョン確認
uv run python --version

# 依存関係更新
uv sync --upgrade

# キャッシュクリア
uv cache clean

# GPU 確認
nvidia-smi
```

#### REST API サーバー

```bash
# API サーバー起動
uv run acestep-api \
  --host 0.0.0.0 \
  --port 8001 \
  --lm_model_path acestep-5Hz-lm-4B
```

---

## トラブルシューティング

### Python バージョンエラー

```bash
# 現在の Python バージョンを確認
uv run python --version

# .python-version を確認
cat .python-version

# 必要に応じて再ピン留め
uv python pin 3.11
```

### CUDA / GPU認識エラー

```bash
# GPU確認
nvidia-smi

# CUDA確認
nvcc --version

# PyTorch でのGPU認識確認
uv run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"
```

### モデルダウンロード失敗

```bash
# ModelScope から試す（中国でホスティング、場合によっては高速）
uv run acestep-download --download-source modelscope

# または手動ダウンロード
uv run python -m pip install huggingface-hub
huggingface-cli download ACE-Step/Ace-Step1.5 --local-dir ./checkpoints
```

### メモリ不足（発生しないはずだが）

```bash
# より小さいLMモデルに切り替え
uv run acestep --lm_model_path acestep-5Hz-lm-1.7B

# または LM を無効化（DiTのみモード）
uv run acestep --init_llm false
```

## 次のステップ

1. ✅ **基本セットアップ完了後:**
   - サンプル音楽を生成してみる
   - 各種生成モードを試す（Simple, Cover, Repaint, Vocal2BGM）
   - 日本語プロンプトでの生成テスト

2. **oto-factory アプリケーション開発:**
   - ACE-Step 1.5 の Python API を使用
   - リアルタイム音生成の実装
   - REST API との連携

3. **カスタマイズ:**
   - LoRA トレーニングで独自スタイルを学習
   - プロンプトエンジニアリングの最適化
   - バッチ生成の活用

## 参考リンク

- [ACE-Step 1.5 日本語インストールガイド](./ACE-Step-1.5/docs/ja/INSTALL.md)
- [日本語チュートリアル](./ACE-Step-1.5/docs/ja/Tutorial.md)
- [Gradio ガイド（日本語）](./ACE-Step-1.5/docs/ja/GRADIO_GUIDE.md)
- [API ドキュメント（日本語）](./ACE-Step-1.5/docs/ja/API.md)
- [GPU 互換性ガイド（日本語）](./ACE-Step-1.5/docs/ja/GPU_COMPATIBILITY.md)

---

## 📝 実行サマリー

### 最短で起動するには（コピペ用）

```bash
# 1. ディレクトリ移動
cd /content/oto-factory/ACE-Step-1.5

# 2. 環境確認
cat .python-version  # "3.11" が表示されればOK

# 3. 依存関係インストール（初回のみ、5-10分）
uv sync

# 4. 環境検証
uv run python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"

# 5. Gradio UI 起動（A100 最適設定）
uv run acestep \
  --language ja \
  --server-name 0.0.0.0 \
  --lm_model_path acestep-5Hz-lm-4B \
  --config_path acestep-v15-turbo \
  --init_service true \
  --backend vllm
```

### 所要時間の目安

| ステップ | 所要時間 | 備考 |
|---------|---------|------|
| 環境確認 | 1分 | すぐ完了 |
| 依存関係インストール | 5-10分 | 初回のみ、PyTorch 等の大容量パッケージをダウンロード |
| 環境検証 | 1分 | インポートテスト |
| モデルダウンロード | 5-10分 | 初回起動時のみ、約10-15GB |
| Gradio UI 起動 | 1-2分 | モデルロード含む |
| **合計（初回）** | **15-20分** | 2回目以降は2-3分で起動 |

### 成功の確認チェックリスト

- [ ] `uv sync` が正常に完了した
- [ ] PyTorch で CUDA が利用可能である（`True`）
- [ ] GPU が認識されている（`NVIDIA A100-SXM4-80GB`）
- [ ] Gradio UI が起動し、公開 URL が表示された
- [ ] UI が日本語で表示される
- [ ] モデルがすべてロードされている（DiT, LM, VAE）
- [ ] 音楽生成テストが成功した
- [ ] 生成速度が高速である（30秒の楽曲が数秒で生成）

---

**結論:** Google Colab + A100 80GB という恵まれた環境であるため、**uv を使用した公式の方法（Option A）**で環境構築を進めることを強く推奨する。Python 3.11 の管理も uv が自動で行うため、手間なく最高品質の設定で ACE-Step 1.5 を動作させることができる。上記の手順に従えば、約15-20分で Gradio UI が起動し、音楽生成を開始できる。
