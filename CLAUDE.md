# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

oto-factory は、音楽生成モデル ACE-Step 1.5 を使用して作業音をリアルタイム生成するアプリケーションである。

## 言語とスタイルのガイドライン

- **回答とドキュメント**: 日本語の常体（である調）を使用すること
- **コメントとログ**: 実装には多めのコメント、docstring、ログを追加し、内容を追いやすく配慮すること
- **参照実装**: `./ACE-Step-1.5` を参考にして実装すること

## 開発環境

### 必須要件

- Python 3.11+ (安定版のみ、プレリリース版は不可)
- パッケージマネージャ: `uv`
- GPU: CUDA推奨、MPS/ROCm/Intel XPU/CPU もサポート

### ACE-Step 1.5 セットアップ

```bash
# サブモジュールの初期化・更新
git submodule update --init --recursive

# 依存関係のインストール
cd ACE-Step-1.5
uv sync
```

## よく使うコマンド

### ACE-Step 1.5 の起動

```bash
# Gradio UI の起動 (http://localhost:7860)
cd ACE-Step-1.5
uv run acestep

# REST API サーバーの起動 (http://localhost:8001)
uv run acestep-api

# モデルのダウンロード（初回起動時は自動）
uv run acestep-download
```

### 開発用コマンド

```bash
# 依存関係の更新
uv sync

# Python インタープリタの起動（仮想環境付き）
uv run python

# テストの実行
cd ACE-Step-1.5
uv run python -m unittest discover -s acestep -p "*_test.py"
```

## アーキテクチャ

### ACE-Step 1.5 の構造

ACE-Step 1.5 は、以下の3つの主要コンポーネントから構成されるハイブリッドアーキテクチャを採用している:

1. **LM (Language Model)**: ユーザークエリを包括的な楽曲設計図に変換する
   - メタデータ、歌詞、キャプションを Chain-of-Thought で生成
   - モデルサイズ: 0.6B / 1.7B / 4B (VRAM に応じて選択)
   - バックエンド: PyTorch (`pt`) または vLLM

2. **DiT (Diffusion Transformer)**: 音楽の生成を担当
   - 高品質な音楽生成（商用モデルと同等以上）
   - A100で2秒未満、RTX 3090で10秒未満で楽曲生成
   - モデル: `acestep-v15-base`, `acestep-v15-sft`, `acestep-v15-turbo`

3. **VAE (Variational Autoencoder)**: 音声のエンコード/デコード

### 主要ディレクトリ

```
ACE-Step-1.5/
├── acestep/                    # メインパッケージ
│   ├── core/                   # コア機能
│   │   ├── generation/         # 音楽生成ハンドラ
│   │   ├── llm/               # LM インターフェース
│   │   └── lora/              # LoRA トレーニング/適用
│   ├── api/                   # REST API
│   ├── gradio_ui/             # Gradio Web UI
│   ├── models/                # モデル定義
│   ├── acestep_v15_pipeline.py # メインパイプライン
│   └── api_server.py          # API サーバー
├── docs/                      # ドキュメント（多言語対応）
│   └── ja/                    # 日本語ドキュメント
└── examples/                  # サンプルコード
```

### 主要モジュール

- `acestep_v15_pipeline.py`: Gradio UI のメインエントリポイント
- `api_server.py`: FastAPI ベースの REST API サーバー
- `inference.py`: 音楽生成の Python API
- `handler.py`: 音楽生成のコアロジック
- `llm_inference.py`: LM 推論の実装
- `gpu_config.py`: GPU 自動検出と最適化

## 実装時の注意事項

### コーディング規約（AGENTS.md より）

1. **スコープの制限**
   - 1つのタスク/PRで1つの問題を解決する
   - 最小限の編集に留める: タスクに必要なファイル/関数のみ変更
   - 無関係なリファクタリングやフォーマット変更を避ける

2. **モジュール分解ポリシー**
   - 単一責任原則に従う
   - 目標モジュールサイズ: ≤150 LOC（推奨）、≤200 LOC（上限）
   - 関数は1つのことを行う（"and" で説明できる場合は分割）

3. **テスト要件**
   - すべての動作変更とバグ修正にテストを追加/更新
   - テストファイル名: `*_test.py` または `test_*.py`
   - `unittest` スタイルを使用
   - 最低限: 成功パステスト、回帰/エッジケーステスト、非ターゲット動作チェック

4. **Python ベストプラクティス**
   - 明示的で読みやすいコードを書く
   - 新規/変更したモジュール、クラス、関数に docstring を必須で追加
   - 実用的な範囲で型ヒントを追加
   - 関数は集中的かつ短く保つ
   - エラーを明示的に処理（bare `except` を避ける）
   - 隠れた状態や意図しない副作用を避ける

5. **文書化**
   - Docstring は簡潔に、目的と主要な入出力を含める
   - コメントは意図が不明瞭な箇所のみに追加
   - ログは実用的に（デバッグ用 `print` をコミットしない）

## 音楽生成の基本概念

### 生成モード

- **Simple Mode**: シンプルな説明文から楽曲全体を生成
- **Query Rewriting**: タグと歌詞を LM が自動拡張
- **Reference Audio**: 参照音声を使用してスタイルをガイド
- **Cover Generation**: 既存音声からカバーを作成
- **Repaint & Edit**: 部分的な音声編集と再生成
- **Vocal2BGM**: ボーカルトラックに伴奏を自動生成

### メタデータ制御

- **duration**: 10秒〜10分（600秒）
- **bpm**: テンポ
- **key/scale**: キー/スケール
- **time_signature**: 拍子

## トラブルシューティング

### VRAM が不足する場合

1. より小さい LM モデルを選択（0.6B → 1.7B → 4B）
2. LM を無効化（DiT のみモード）
3. INT8 量子化を有効化
4. CPU オフロードを使用

### モデルのダウンロードに失敗する場合

```bash
# 手動でモデルをダウンロード
cd ACE-Step-1.5
uv run acestep-download
```

## リファレンス

- [ACE-Step 1.5 README](./ACE-Step-1.5/README.md)
- [日本語インストールガイド](./ACE-Step-1.5/docs/ja/INSTALL.md)
- [日本語チュートリアル](./ACE-Step-1.5/docs/ja/Tutorial.md)
- [Gradio ガイド（日本語）](./ACE-Step-1.5/docs/ja/GRADIO_GUIDE.md)
- [API ドキュメント（日本語）](./ACE-Step-1.5/docs/ja/API.md)
- [推論ガイド（日本語）](./ACE-Step-1.5/docs/ja/INFERENCE.md)
- [エージェント向けガイド](./ACE-Step-1.5/AGENTS.md)
