import pytest
from unittest.mock import MagicMock

# --- パッチを適用してからアプリケーションをインポートする ---
# main.pyはインポート時にGCP関連のコードが実行されるため、
# 先にモックで置き換えておく必要がある

import sys

# モックするモジュールを作成
mock_config = MagicMock()
mock_config.APP_ID = "TEST_APP_ID"
mock_config.GCS_BUCKET_NAME = "test-bucket"

mock_estat_handler = MagicMock()
mock_storage = MagicMock()

# sys.modulesに登録して、後続のimportでモックが使われるようにする
sys.modules["config"] = mock_config
sys.modules["estat_handler"] = mock_estat_handler
sys.modules["google.cloud.storage"] = mock_storage

# モックの設定後にアプリケーション本体をインポート
from src.main import app

@pytest.fixture
def client():
    """Flaskのテスト用クライアントを返すフィクスチャ"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def reset_mocks():
    """各テストの実行前にモックの状態をリセットする"""
    mock_config.reset_mock()
    mock_estat_handler.reset_mock()
    mock_storage.reset_mock()


def test_renew_success(client):
    """データ更新が成功するケースのテスト"""
    # --- 準備 ---
    # データ取得関数がダミーの辞書を返すように設定
    dummy_data = {"2020": {"東京都": {"total_population": 14000000}}}
    mock_estat_handler.fetch_and_process_population_data.return_value = dummy_data

    # GCSクライアントのモックを設定
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_storage.Client.return_value.bucket.return_value = mock_bucket

    # --- 実行 ---
    response = client.post("/api/v1/renew")

    # --- 検証 ---
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["message"] == f"Data successfully renewed and saved to gs://{mock_config.GCS_BUCKET_NAME}/population_by_year_prefecture.json"

    # 外部サービスが正しく呼び出されたか確認
    mock_estat_handler.fetch_and_process_population_data.assert_called_once_with(app_id=mock_config.APP_ID)
    mock_storage.Client.return_value.bucket.assert_called_once_with(mock_config.GCS_BUCKET_NAME)
    mock_bucket.blob.assert_called_once_with("population_by_year_prefecture.json")
    mock_blob.upload_from_string.assert_called_once()


def test_renew_fetch_failure(client):
    """データ取得に失敗するケースのテスト"""
    # --- 準備 ---
    # データ取得関数がNoneを返すように設定
    mock_estat_handler.fetch_and_process_population_data.return_value = None
    mock_gcs_client = mock_storage.Client.return_value

    # --- 実行 ---
    response = client.post("/api/v1/renew")

    # --- 検証 ---
    assert response.status_code == 500
    json_data = response.get_json()
    assert json_data["status"] == "error"
    assert json_data["message"] == "Failed to retrieve data from e-Stat."

    # GCSへのアップロードが実行されていないことを確認
    mock_gcs_client.bucket.assert_not_called()
