# MacBook Air から Google Colab の Gradio アプリに接続する方法

Google Colab 環境で動作している Gradio アプリに、ローカルの MacBook Air から接続する方法を説明する。

---

## Option A: Gradio --share オプション（最もシンプル）⭐

**推奨理由:**
- SSH 不要、最もシンプル
- Gradio が自動的に公開 URL を生成
- 72時間有効な公開リンク
- MacBook Air から直接ブラウザでアクセス可能

### 手順

#### 1. Colab で現在のプロセスを停止

```bash
# 現在実行中の acestep プロセスを停止
pkill -f acestep

# 停止確認
ps aux | grep acestep | grep -v grep
```

#### 2. --share オプション付きで再起動

```bash
cd /content/oto-factory/ACE-Step-1.5

uv run acestep \
  --language ja \
  --server-name 0.0.0.0 \
  --port 7860 \
  --lm_model_path acestep-5Hz-lm-4B \
  --config_path acestep-v15-turbo \
  --init_service true \
  --backend vllm \
  --share
```

#### 3. 公開 URL を取得

起動ログに以下のような URL が表示される：

```
Running on local URL:  http://0.0.0.0:7860
Running on public URL: https://xxxxxxxxxxxxx.gradio.live
```

#### 4. MacBook Air からアクセス

MacBook Air のブラウザで公開 URL を開く：

```
https://xxxxxxxxxxxxx.gradio.live
```

### メリット

- ✅ 最もシンプル（SSH 不要）
- ✅ すぐに使える
- ✅ 自動的に HTTPS で暗号化
- ✅ どこからでもアクセス可能

### デメリット

- ❌ URL が毎回変わる
- ❌ 72時間で URL が無効になる
- ❌ インターネット経由（遅延がある場合あり）

---

## Option B: ngrok でポート公開（SSH 不要）

ngrok を使って固定的なトンネルを作成する方法。

### 手順

#### 1. ngrok をインストール

```bash
# Colab に ngrok をインストール
cd /tmp
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

#### 2. ngrok アカウントのセットアップ（初回のみ）

1. https://ngrok.com/ でアカウント作成（無料）
2. AuthToken を取得
3. Colab で設定：

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

#### 3. トンネルを起動

```bash
# バックグラウンドで ngrok を起動
nohup ngrok http 7860 > /tmp/ngrok.log 2>&1 &

# 数秒待機
sleep 5

# 公開 URL を確認
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"
```

#### 4. MacBook Air からアクセス

表示された URL（例: `https://xxxx-xxxx-xxxx.ngrok-free.app`）をブラウザで開く。

### メリット

- ✅ SSH 不要
- ✅ ngrok の管理画面でトラフィックを確認可能
- ✅ 有料プランで固定 URL が使える

### デメリット

- ❌ 無料プランは URL が毎回変わる
- ❌ 無料プランは接続数制限あり
- ❌ ngrok アカウントが必要

---

## Option C: SSH サーバー + ngrok + SSH ポートフォワーディング（本格的）

本格的な SSH ポートフォワーディングを使用する方法。

### 概要

```
MacBook Air → SSH → ngrok → Colab (SSH Server) → localhost:7860 (Gradio)
```

### 手順

#### Phase 1: Colab に SSH サーバーをセットアップ

```bash
# SSH サーバーをインストール
sudo apt-get update -qq
sudo apt-get install -y openssh-server > /dev/null

# SSH サーバーの設定
sudo sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# devuser のパスワードを設定
echo "devuser:your_password_here" | sudo chpasswd

# SSH サーバーを起動
sudo service ssh start

# SSH サーバーが起動しているか確認
sudo service ssh status
```

#### Phase 2: ngrok で SSH ポートを公開

```bash
# ngrok をインストール（未インストールの場合）
cd /tmp
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# ngrok の AuthToken を設定（初回のみ）
ngrok config add-authtoken YOUR_AUTHTOKEN

# SSH ポート（22）を公開
nohup ngrok tcp 22 > /tmp/ngrok-ssh.log 2>&1 &

# 数秒待機
sleep 5

# SSH 接続情報を取得
curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
tunnels = json.load(sys.stdin)['tunnels']
for t in tunnels:
    if t['proto'] == 'tcp':
        url = t['public_url']
        host = url.replace('tcp://', '').split(':')[0]
        port = url.replace('tcp://', '').split(':')[1]
        print(f'SSH Host: {host}')
        print(f'SSH Port: {port}')
        print(f'')
        print(f'Connect from Mac:')
        print(f'ssh -L 7860:localhost:7860 devuser@{host} -p {port}')
"
```

#### Phase 3: MacBook Air から SSH ポートフォワーディング

MacBook Air のターミナルで実行：

```bash
# SSH ポートフォワーディングで接続
ssh -L 7860:localhost:7860 devuser@{ngrok_host} -p {ngrok_port}

# パスワードを入力（Colab で設定したパスワード）
```

接続成功後、MacBook Air のブラウザで以下にアクセス：

```
http://localhost:7860
```

### メリット

- ✅ 本格的な SSH ポートフォワーディング
- ✅ ローカルホストとして接続（localhost:7860）
- ✅ SSH の暗号化で安全
- ✅ SSH を介して他のコマンドも実行可能

### デメリット

- ❌ セットアップが複雑
- ❌ SSH サーバーの設定が必要
- ❌ ngrok アカウントが必要
- ❌ Colab セッションが切れると再設定が必要

---

## 方法の比較

| 項目 | Option A: --share | Option B: ngrok | Option C: SSH + ngrok |
|------|------------------|-----------------|----------------------|
| **難易度** | ⭐ 簡単 | ⭐⭐ 中程度 | ⭐⭐⭐ 難しい |
| **セットアップ時間** | 1分 | 5分 | 10分 |
| **SSH 必要** | 不要 | 不要 | 必要 |
| **外部サービス** | なし | ngrok | ngrok |
| **アクセス URL** | gradio.live | ngrok-free.app | localhost:7860 |
| **URL の永続性** | 72時間 | セッション中 | セッション中 |
| **ローカル接続** | ❌ | ❌ | ✅ |
| **推奨度** | ⭐⭐⭐ | ⭐⭐ | ⭐ |

---

## 推奨される方法

### 初めて使う場合: Option A (--share)

最もシンプルで、すぐに使える。

```bash
# Colab で実行
pkill -f acestep
uv run acestep --language ja --server-name 0.0.0.0 --share
```

### より柔軟に使いたい場合: Option B (ngrok)

ngrok の管理画面でトラフィックを確認したい場合。

### SSH 接続を本格的に使いたい場合: Option C (SSH + ngrok)

SSH 経由で Colab にアクセスし、他のコマンドも実行したい場合。

---

## クイックスタート（Option A 推奨）

### 1. Colab で実行

```bash
cd /content/oto-factory/ACE-Step-1.5
pkill -f acestep
uv run acestep --language ja --server-name 0.0.0.0 --share
```

### 2. 出力から公開 URL をコピー

```
Running on public URL: https://xxxxxxxxxxxxx.gradio.live
```

### 3. MacBook Air のブラウザで開く

URL をブラウザに貼り付けて開く。

**完了！** 🎉

---

## トラブルシューティング

### Gradio --share が失敗する

```bash
# タイムアウトを増やして再試行
uv run acestep --language ja --server-name 0.0.0.0 --share --share-timeout 600
```

### ngrok が起動しない

```bash
# ngrok のプロセスを確認
ps aux | grep ngrok

# ログを確認
cat /tmp/ngrok.log
```

### SSH 接続がタイムアウトする

```bash
# Colab で SSH サーバーの状態を確認
sudo service ssh status

# 再起動
sudo service ssh restart
```

### MacBook Air から接続できない

```bash
# Colab のファイアウォール確認（通常は不要）
sudo ufw status

# ポートが開いているか確認
netstat -tlnp | grep 7860
```

---

## セキュリティ上の注意

### Option A (--share)
- gradio.live URL は72時間有効
- URL を知っている人は誰でもアクセス可能
- 重要なデータは扱わない

### Option B (ngrok)
- 無料プランは URL が公開される
- Basic 認証を追加することを推奨

### Option C (SSH + ngrok)
- 強力なパスワードを設定する
- SSH キー認証を使用することを推奨
- Colab セッション終了後は自動的に無効になる
