# oto-factory

## 概要

このプロジェクトは音楽生成モデル[Ace Step 1.5](https://github.com/ace-step/ACE-Step-1.5)を使用して、作業音をリアルタイム生成するアプリケーションを提供する。

## 環境構築

### Google Colab A100 でのセットアップ

詳細なインストール手順は [`install.md`](./install.md) を参照のこと。

**クイックスタート:**

```bash
# 1. ディレクトリ移動
cd /content/oto-factory/ACE-Step-1.5

# 2. 依存関係インストール（初回のみ）
uv sync

# 3. Gradio UI 起動
uv run acestep --language ja --server-name 0.0.0.0
```

詳細は以下を参照：
- [環境構築の詳細手順](./install.md)
- [環境構築プラン](./claude_plan.md)

### ローカルマシンからのアクセス

#### SSH ポートフォワーディング（推奨）

既に SSH 接続が確立されている場合、ポートフォワーディングで Gradio UI にアクセスできる。

**MacBook Air から接続:**

```bash
# ポートフォワーディングで接続
ssh -L 7860:localhost:7860 colab

# ブラウザで開く
http://localhost:7860
```

**SSH 設定に永続的に追加:**

`~/.ssh/config` に以下を追加：

```
Host colab
  HostName your-cloudflare-tunnel.trycloudflare.com
  User devuser
  ProxyCommand cloudflared access ssh --hostname %h
  IdentityFile ~/.ssh/id_ed25519
  LocalForward 7860 localhost:7860
```

設定後は通常の SSH 接続で自動的にポートフォワーディングが有効になる：

```bash
ssh colab
```

詳細は [`mac-connection-guide.md`](./mac-connection-guide.md) を参照のこと。

#### その他のアクセス方法

- **Gradio --share オプション**: `--share` フラグで公開 URL を生成
- **ngrok**: トンネルを作成して公開 URL を生成

詳細は [`ssh-forwarding-guide.md`](./ssh-forwarding-guide.md) を参照のこと。

## プロジェクト構成

```
oto-factory/
├── ACE-Step-1.5/           # ACE-Step 1.5 サブモジュール
├── README.md               # 本ファイル
├── CLAUDE.md               # Claude Code 向けガイド
├── AGENTS.md               # エージェント向けガイドライン
├── install.md              # Google Colab A100 インストールガイド
├── claude_plan.md          # 環境構築プラン
├── design_codex.md         # プロトタイプ設計書
├── ssh-forwarding-guide.md # SSH ポートフォワーディング全ガイド
└── mac-connection-guide.md # MacBook Air 接続ガイド
```

## ドキュメント

### 環境構築
- **[install.md](./install.md)**: Google Colab A100 での詳細なインストール手順
- **[claude_plan.md](./claude_plan.md)**: 環境構築方法の比較と推奨プラン
- **[mac-connection-guide.md](./mac-connection-guide.md)**: MacBook Air からの接続手順
- **[ssh-forwarding-guide.md](./ssh-forwarding-guide.md)**: すべてのアクセス方法の比較

### アプリケーション
- **[design_codex.md](./design_codex.md)**: プロトタイプ設計書

### 開発ガイド
- **[CLAUDE.md](./CLAUDE.md)**: Claude Code 向けの開発ガイド
- **[AGENTS.md](./AGENTS.md)**: エージェント向けガイドライン

## エージェントへのお願い

- 回答とドキュメントは日本語の常体（で・ある調）を使用する
- 実装にはコメントやdocstringやログを多めに追加し、内容を追いやすく配慮する
- ./ACE-Step-1.5を参考にして実装すること

## 参考リンク

- [ACE-Step 1.5 公式リポジトリ](https://github.com/ace-step/ACE-Step-1.5)
- [ACE-Step 1.5 日本語ドキュメント](./ACE-Step-1.5/docs/ja/)
