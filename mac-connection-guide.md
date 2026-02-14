# MacBook Air から Gradio UI に接続する手順

既存の SSH 接続（Cloudflare Tunnel 経由）を使って、SSH ポートフォワーディングで Gradio UI にアクセスする。

---

## 前提条件

- ✅ Cloudflare Tunnel が設定済み
- ✅ SSH 接続が確立済み（`~/.ssh/config` に `colab` ホストが設定済み）
- ✅ Colab で Gradio が実行中（port 7860）

---

## 接続手順

### 方法 1: コマンドラインで接続（すぐに試せる）

#### Step 1: SSH ポートフォワーディングで接続

MacBook Air のターミナルで実行：

```bash
ssh -L 7860:localhost:7860 colab
```

**コマンドの意味:**
- `-L 7860:localhost:7860`: ローカルの 7860 ポートを Colab の localhost:7860 に転送
- `colab`: SSH 設定の Host 名

**期待される出力:**

```
Welcome to Ubuntu 22.04.5 LTS (GNU/Linux 6.6.105+ x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

devuser@c9131c5b665f:~$
```

#### Step 2: ブラウザでアクセス

MacBook Air で **新しいターミナルウィンドウ** を開くか、ブラウザで以下を開く：

```
http://localhost:7860
```

**期待される画面:**

```
🎛️ ACE-Step V1.5 プレイグラウンド💡
オープンソース音楽生成の限界を押し広げる
```

日本語の Gradio UI が表示される。

#### Step 3: 音楽生成テスト

1. **「🎵 音楽生成」タブを開く**
2. **Simple Mode を選択**
3. **プロンプトを入力:**
   ```
   穏やかなピアノのインストゥルメンタル、リラックスできる雰囲気
   ```
4. **Duration: 30 秒**
5. **Generate をクリック**

A100 GPU で数秒で生成される。

---

### 方法 2: SSH 設定に永続的に追加（推奨）

#### Step 1: SSH 設定ファイルを編集

```bash
nano ~/.ssh/config
```

または

```bash
vim ~/.ssh/config
```

#### Step 2: LocalForward を追加

既存の `Host colab` セクションに `LocalForward` 行を追加：

```
Host colab
  HostName microphone-supplemental-educated-university.trycloudflare.com
  User devuser
  ProxyCommand cloudflared access ssh --hostname %h
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  ServerAliveInterval 60
  ServerAliveCountMax 3
  LocalForward 7860 localhost:7860
```

#### Step 3: 保存して閉じる

- nano: `Ctrl+O`, `Enter`, `Ctrl+X`
- vim: `Esc`, `:wq`, `Enter`

#### Step 4: 接続

設定後は、通常の SSH 接続だけで自動的にポートフォワーディングが有効になる：

```bash
ssh colab
```

ブラウザで `http://localhost:7860` を開くだけ。

---

### 方法 3: バックグラウンドで実行（SSH セッションを開いたままにしたくない場合）

SSH セッションをバックグラウンドで維持し、ターミナルを占有しない方法：

```bash
ssh -f -N -L 7860:localhost:7860 colab
```

**オプション説明:**
- `-f`: バックグラウンドで実行
- `-N`: リモートコマンドを実行しない（ポートフォワーディングのみ）
- `-L`: ローカルポートフォワーディング

**接続を切る場合:**

```bash
# プロセスを探す
ps aux | grep "ssh.*colab" | grep -v grep

# PID を確認して終了
kill <PID>
```

または：

```bash
pkill -f "ssh.*colab"
```

---

## 接続確認コマンド

### MacBook Air 側で確認

```bash
# ポートフォワーディングが有効か確認
netstat -an | grep 7860

# または
lsof -i :7860

# Gradio にアクセスできるか確認
curl http://localhost:7860 | head -20
```

**期待される出力:**

```html
<!doctype html>
<html
	lang="en"
	...
```

---

## トラブルシューティング

### 1. "Connection refused" エラー

**原因:** Colab で Gradio が起動していない

**解決策:**

Colab 側で確認：

```bash
# SSH で Colab に接続
ssh colab

# Gradio のプロセスを確認
ps aux | grep acestep | grep -v grep

# 起動していない場合、起動
cd /content/oto-factory/ACE-Step-1.5
uv run acestep --language ja --server-name 0.0.0.0
```

### 2. "Address already in use" エラー

**原因:** MacBook Air の 7860 ポートが既に使用されている

**解決策:**

```bash
# ポートを使用しているプロセスを確認
lsof -i :7860

# プロセスを終了
kill <PID>

# または別のポートを使用
ssh -L 7861:localhost:7860 colab
# ブラウザで http://localhost:7861 を開く
```

### 3. SSH 接続が切れる

**原因:** ネットワーク不安定、タイムアウト

**解決策:**

SSH 設定に KeepAlive を追加（既に設定済み）：

```
ServerAliveInterval 60
ServerAliveCountMax 3
```

または、再接続：

```bash
ssh -L 7860:localhost:7860 colab
```

### 4. ブラウザでアクセスできない

**チェックリスト:**

1. SSH 接続が確立されているか確認
   ```bash
   ssh -L 7860:localhost:7860 colab
   # 接続後、別のターミナルでブラウザを開く
   ```

2. ポートフォワーディングが有効か確認
   ```bash
   lsof -i :7860
   ```

3. Colab で Gradio が起動しているか確認
   ```bash
   # SSH セッション内で
   curl http://localhost:7860
   ```

---

## 複数ポートを転送する場合

他のサービスも同時に転送したい場合：

```bash
ssh -L 7860:localhost:7860 -L 8000:localhost:8000 colab
```

または、SSH 設定に複数追加：

```
Host colab
  ...
  LocalForward 7860 localhost:7860
  LocalForward 8000 localhost:8000
  LocalForward 8001 localhost:8001
```

---

## パフォーマンスの最適化

### 圧縮を有効にする

大量のデータを転送する場合、SSH 圧縮を有効にする：

```bash
ssh -C -L 7860:localhost:7860 colab
```

または、SSH 設定に追加：

```
Host colab
  ...
  Compression yes
```

### TCP KeepAlive を調整

```
Host colab
  ...
  TCPKeepAlive yes
  ServerAliveInterval 30
  ServerAliveCountMax 6
```

---

## セキュリティ上の注意

### ローカルホストにバインド

デフォルトでは `localhost` にバインドされるため、MacBook Air 上でのみアクセス可能である。これは安全である。

もし LAN 内の他のデバイスからもアクセスしたい場合：

```bash
ssh -L 0.0.0.0:7860:localhost:7860 colab
# 危険: LAN 内の全デバイスからアクセス可能になる
```

**推奨:** `localhost` バインドのままにする。

---

## クイックリファレンス

### 基本接続

```bash
ssh -L 7860:localhost:7860 colab
```

### バックグラウンド接続

```bash
ssh -f -N -L 7860:localhost:7860 colab
```

### 接続確認

```bash
curl http://localhost:7860
```

### 接続を切る

```bash
pkill -f "ssh.*colab"
```

### ブラウザでアクセス

```
http://localhost:7860
```

---

## まとめ

1. **MacBook Air のターミナルで:**
   ```bash
   ssh -L 7860:localhost:7860 colab
   ```

2. **ブラウザで開く:**
   ```
   http://localhost:7860
   ```

3. **音楽生成を楽しむ！** 🎵

これで、MacBook Air から Colab の Gradio UI に安全かつ高速に接続できる。
