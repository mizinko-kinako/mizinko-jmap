from google.cloud import secretmanager
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（ローカル開発用）
load_dotenv()

# Secret Managerクライアントを初期化
client = secretmanager.SecretManagerServiceClient()

# GCPプロジェクトIDを取得
# 1. Cloud Run環境で自動的に設定される環境変数 "GCP_PROJECT" を優先
# 2. 1がない場合、ローカルの.envファイルなどに記載された "GCP_PROJECT" を使用
PROJECT_ID = os.getenv("GCP_PROJECT")

def get_secret(secret_id: str, version_id: str = "latest") -> str:
    """Google Secret Managerから最新のシークレットを取得する"""
    # PROJECT_IDが取得できているかここで改めて確認
    if not PROJECT_ID:
        # .envファイルにもGCP_PROJECTが設定されていない場合
        raise ValueError(
            "GCP_PROJECT environment variable is not set. "
            "Please set it in your OS environment or in a .env file for local development."
        )

    # シークレットの完全なリソース名を構築
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    
    try:
        # シークレットにアクセス
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error accessing secret '{secret_id}': {e}")
        raise

# アプリケーションで利用する設定値をSecret Managerから取得
try:
    APP_ID = get_secret("jmap-app-id")
    GCS_BUCKET_NAME = get_secret("jmap-gcs-bucket-name")
except Exception as e:
    # アプリケーション起動時にシークレットが取得できない場合は、エラーを明確にする
    print("Could not retrieve secrets from Secret Manager. Please check configuration and permissions.")
    raise
