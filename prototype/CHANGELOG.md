# プロトタイプ変更履歴

## 2026-02-14: API クライアント修正とテスト成功

### 修正内容

#### 1. `/query_result` エンドポイントのパラメータ修正
**問題**: API に `{"task_id": "..."}` を送信していたが、API は `task_id_list` を期待していた。

**修正**:
```python
# 修正前
payload = {"task_id": task_id}

# 修正後
payload = {"task_id_list": [task_id]}
```

**影響ファイル**: `ace_client.py`, `test_api.py`

#### 2. レスポンス解析の改善
**問題**: API のレスポンス構造が複雑で、正しく解析できていなかった。

**API レスポンス構造**:
```json
{
  "data": [
    {
      "task_id": "...",
      "result": "[{...}]",  // JSON 文字列
      "status": 0|1|2,
      "progress_text": "..."
    }
  ],
  "code": 200,
  "error": null,
  "timestamp": 1771060000000,
  "extra": null
}
```

**修正**:
- `data` フィールドからリストを取得
- `result` フィールドの JSON 文字列をパース
- 空データ `[]` のハンドリング

**影響ファイル**: `ace_client.py`, `test_api.py`

#### 3. 音声ファイルフィールドの修正
**問題**: API は `file` フィールドに音声パスを返すが、コードは `audio_path` を期待していた。

**修正**:
```python
# 修正前
if save_to and "audio_path" in data:
    audio_path = data["audio_path"]

# 修正後
audio_path = data.get("audio_path") or data.get("file")
if save_to and audio_path:
    audio_url = f"{self.base_url}{audio_path}"
```

**影響ファイル**: `ace_client.py`

#### 4. エラーハンドリングの改善
**問題**: 無限ループと連続失敗時のバックオフがなかった（以前のコミットで修正済み）。

**修正**:
- 指数バックオフ（2^n 秒、最大 60 秒）
- 連続失敗カウンタと警告メッセージ

**影響ファイル**: `generator_loop.py`

### テスト結果

#### 単一セグメント生成テスト (`test_single_segment.py`)
```
✅ タスク投入: 成功
✅ タスク完了: 約3秒
✅ 音声ファイル: 157 KB (MP3)
✅ 生成速度: 1.20秒/曲
```

#### プロトタイプ動作確認 (`test_prototype.py`)
```
✅ セグメント#1: 4.5秒で生成完了 (157 KB)
✅ セグメント#2: 3.0秒で生成完了 (157 KB)
✅ キューイング: 2セグメント
✅ セグメント取得: 成功
```

### 追加ファイル

- `test_api.py`: API エンドポイントの基本動作確認
- `test_single_segment.py`: 単一セグメント生成テスト
- `test_prototype.py`: プロトタイプ全体の動作確認

### パフォーマンス

- **生成速度**: 約 1.2〜2.4 秒/曲（10秒の音楽）
- **セグメント生成**: 3〜5 秒/セグメント
- **ダウンロード**: 157 KB/セグメント（MP3 形式）

### 次のステップ

1. `player.py` の動作確認（音声再生機能）
2. `app.py` の完全な動作確認（生成 + 再生）
3. MacBook Air からのポートフォワーディング経由での動作確認
4. ドキュメント更新
