from google.cloud import secretmanager
import os

# Secret Managerクライアントを初期化
client = secretmanager.SecretManagerServiceClient()

# GCPプロジェクトIDは、Cloud Run環境では自動的に設定される環境変数から取得
PROJECT_ID = os.getenv("GCP_PROJECT")

def get_secret(secret_id: str, version_id: str = "latest") -> str:
    """Google Secret Managerから最新のシークレットを取得する"""
    if not PROJECT_ID:
        # ローカル環境などでGCP_PROJECTが設定されていない場合のフォールバック
        # gcloud config get-value project コマンドで取得するなど、代替手段を検討
        raise ValueError("GCP_PROJECT environment variable is not set.")

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
