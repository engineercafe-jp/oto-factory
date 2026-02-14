"""
ACE-Step API の動作確認用テストスクリプト

API サーバーが正しく動作しているかを確認する。
"""

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:8001"


def test_health():
    """ヘルスチェック"""
    print("=" * 60)
    print("1. Health Check")
    print("=" * 60)

    url = f"{API_BASE_URL}/health"
    response = requests.get(url)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_release_task():
    """タスク投入テスト"""
    print("=" * 60)
    print("2. Release Task Test")
    print("=" * 60)

    url = f"{API_BASE_URL}/release_task"
    payload = {
        "task_type": "text2music",
        "text": "穏やかなピアノのインストゥルメンタル",
        "thinking": True,
        "lm_backend": "vllm",
        "lm_model_path": "acestep-5Hz-lm-0.6B",
        "config_path": "acestep-v15-turbo",
        "audio_duration": 10,  # 短い時間でテスト
    }

    print(f"Request Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()

    response = requests.post(url, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

    # task_id を取得
    result = response.json()
    if isinstance(result, dict) and "data" in result:
        task_id = result["data"].get("task_id")
    else:
        task_id = result.get("task_id")

    return task_id


def test_query_result(task_id):
    """結果確認テスト"""
    print("=" * 60)
    print("3. Query Result Test")
    print("=" * 60)

    url = f"{API_BASE_URL}/query_result"
    # API は task_id_list（リスト形式）を期待している
    payload = {"task_id_list": [task_id]}

    max_attempts = 60  # 最大60回試行（約1分）
    for attempt in range(max_attempts):
        response = requests.post(url, json=payload)

        print(f"Attempt {attempt + 1}: Status Code {response.status_code}")

        result = response.json()

        # デバッグ: 最初の試行で構造を確認
        if attempt == 0:
            print(f"  Debug - Raw Response: {json.dumps(result, indent=2, ensure_ascii=False)}")

        # ラッパー形式の場合: {"data": [{"task_id": "...", "result": "...", "status": 0|1|2}], ...}
        if isinstance(result, dict) and "data" in result:
            data_list = result.get("data", [])
            if not data_list or len(data_list) == 0:
                print(f"  タスク未登録")
                status = None
                data = {}
            else:
                # 最初の要素を取得
                item = data_list[0]
                status = item.get("status")

                # result フィールドは JSON 文字列の場合がある
                result_data = item.get("result", "{}")
                if isinstance(result_data, str):
                    try:
                        result_data = json.loads(result_data) if result_data else {}
                    except json.JSONDecodeError:
                        result_data = {}

                # result_data がリストの場合は最初の要素を取得
                if isinstance(result_data, list) and len(result_data) > 0:
                    result_data = result_data[0]

                data = result_data if isinstance(result_data, dict) else {}
                data["status"] = status
        else:
            # 直接レスポンスの場合（非推奨）
            status = result.get("status")
            data = result

        print(f"  Task Status: {status}")

        if status == 1:  # 成功
            print("  ✅ タスク成功！")
            print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return data
        elif status == 2:  # 失敗
            print("  ❌ タスク失敗")
            print(f"  Error: {data.get('error', data.get('message', 'Unknown'))}")
            return None
        else:
            print("  ⏳ 実行中...")
            time.sleep(1)

    print("  ⏰ タイムアウト")
    return None


def main():
    """メインテスト"""
    try:
        # 1. Health Check
        test_health()

        # 2. タスク投入
        task_id = test_release_task()

        if not task_id:
            print("❌ タスク投入失敗")
            return

        print(f"✅ Task ID: {task_id}")
        print()

        # 3. 結果確認
        result = test_query_result(task_id)

        if result:
            print("=" * 60)
            print("✅ テスト成功！")
            print("=" * 60)
        else:
            print("=" * 60)
            print("❌ テスト失敗")
            print("=" * 60)

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
