import os
import json
from flask import Flask, jsonify
from google.cloud import storage

# config.pyでSecret Managerからシークレットが読み込まれる
# 読み込みに失敗した場合は、起動時に例外が発生してアプリが停止する
from config import APP_ID, GCS_BUCKET_NAME
from estat_handler import fetch_and_process_population_data

# Flaskアプリケーションの初期化
app = Flask(__name__)

# Google Cloud Storage クライアントの初期化
# Cloud Runのサービスアカウントが自動的に認証情報として使用される
storage_client = storage.Client()

@app.route("/api/v1/renew", methods=['POST'])
def renew_population_data():
    """
    e-Statから最新の人口統計データを取得し、結果をGCSにJSONファイルとして保存する。
    """
    print("API endpoint /api/v1/renew was hit.")

    # --- データ取得と処理 ---
    # APP_IDはconfig.pyから正常にインポートされていることが保証されている
    print(f"Fetching data using APP_ID: {APP_ID[:4]}...")
    population_data = fetch_and_process_population_data(app_id=APP_ID)

    if not population_data:
        print("Error: Failed to fetch or process population data.")
        return jsonify({"status": "error", "message": "Failed to retrieve data from e-Stat."}), 500

    # --- GCSへのアップロード ---
    try:
        # GCS_BUCKET_NAMEはconfig.pyから正常にインポートされている
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_name = "population_by_year_prefecture.json"
        blob = bucket.blob(blob_name)

        print(f"Uploading data to gs://{GCS_BUCKET_NAME}/{blob_name}")
        
        # 辞書をJSON形式の文字列に変換してアップロード
        blob.upload_from_string(
            json.dumps(population_data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )

        print("Successfully uploaded to GCS.")
        return jsonify({
            "status": "success", 
            "message": f"Data successfully renewed and saved to gs://{GCS_BUCKET_NAME}/{blob_name}"
        })

    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        return jsonify({"status": "error", "message": f"An error occurred while uploading to GCS: {e}"}), 500

if __name__ == "__main__":
    # Cloud RunではGunicornが使われるが、ローカル開発用にFlaskの開発サーバーを起動
    # ローカルで実行する場合、事前にgcloud auth application-default loginの実行が必要
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
