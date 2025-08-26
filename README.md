# 人口統計データ取得・保存アプリケーション

このアプリケーションは、e-Stat APIから年度ごと・都道府県別の総人口データを取得し、指定されたGoogle Cloud Storage (GCS) バケットにJSONファイルとして保存するCloud Runサービスです。

CI/CDパイプラインが設定されており、GitHubへのプッシュをトリガーに、自動テストとCloud Runへのデプロイが実行されます。

## 主な機能

- **APIエンドポイント:** `/api/v1/renew` (POSTリクエスト)
- **データソース:** [e-Stat API (政府統計の総合窓口)](https://www.e-stat.go.jp/)
- **保存先:** Google Cloud Storage
- **テスト:** `pytest`による単体テスト
- **CI/CD:** GitHubとGoogle Cloud Buildを連携

## ファイル構成

```
.
├── src/                  # アプリケーションのソースコード
├── tests/                # 自動テストコード
├── .gitignore
├── cloudbuild.yaml       # CI/CDパイプライン定義ファイル
├── Dockerfile            # コンテナビルド用の設計図
├── requirements.txt      # Pythonの依存ライブラリ一覧
├── start.sh              # コンテナ起動用スクリプト (本番用)
├── start_local.sh        # ローカル開発用スクリプト
└── README.md             # このファイル
```

---

## 1. 事前準備 (初回のみ)

### 1.1. Google Cloud プロジェクトの設定

#### 1. 必要なAPIを有効化
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage-component.googleapis.com secretmanager.googleapis.com iam.googleapis.com
```

#### 2. Secret Managerでシークレットを作成
```bash
# e-StatのAPP IDをシークレットとして保存 (YOUR_APP_ID_HERE を実際のIDに置き換える)
printf "YOUR_APP_ID_HERE" | gcloud secrets create jmap-app-id --data-file=-

# GCSのバケット名をシークレットとして保存 (YOUR_BUCKET_NAME_HERE を実際のバケット名に置き換える)
printf "YOUR_BUCKET_NAME_HERE" | gcloud secrets create jmap-gcs-bucket-name --data-file=-
```

#### 3. Google Cloud Storageバケットを作成
アプリケーションがデータを保存するためのGCSバケットを作成します。バケット名は**全世界で一意**にする必要があります。
```bash
# YOUR_BUCKET_NAME_HERE を実際のバケット名に置き換える
gcloud storage buckets create gs://YOUR_BUCKET_NAME_HERE --location=asia-northeast1
```

#### 4. Cloud RunとCloud Buildのサービスアカウントに権限を付与

```bash
# プロジェクト番号とプロジェクトIDを取得
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
PROJECT_ID=$(gcloud config get-value project)

# Cloud Runのサービスアカウント (デフォルトの場合)
RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
# Cloud Buildのサービスアカウント
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Cloud RunのSAにSecret Managerへのアクセス権を付与
gcloud secrets add-iam-policy-binding jmap-app-id --member="serviceAccount:${RUN_SA}" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding jmap-gcs-bucket-name --member="serviceAccount:${RUN_SA}" --role="roles/secretmanager.secretAccessor"

# Cloud RunのSAにGCSバケットへの書き込み権限を付与 (YOUR_BUCKET_NAME_HERE を実際のバケット名に置き換える)
gcloud storage buckets add-iam-policy-binding gs://YOUR_BUCKET_NAME_HERE --member="serviceAccount:${RUN_SA}" --role="roles/storage.objectAdmin"

# Cloud BuildのSAにCloud Runへのデプロイ権限と、サービスアカウントのなりすまし権限を付与
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:${BUILD_SA}" --role="roles/run.admin"
gcloud iam service-accounts add-iam-policy-binding ${RUN_SA} --member="serviceAccount:${BUILD_SA}" --role="roles/iam.serviceAccountUser"
```

### 1.2. GitHubとCloud Buildの連携

1.  Google Cloudコンソールで「Cloud Build」に移動し、「トリガー」タブを開きます。
2.  「リポジトリを接続」を選択し、このプロジェクトのGitHubリポジトリを接続します。
3.  「トリガーを作成」をクリックします。
    *   **名前:** `deploy-on-push` など分かりやすい名前を入力
    *   **イベント:** `ブランチにプッシュ`
    *   **ソース:** 先ほど接続したリポジトリと、対象のブランチ（例: `main`）を選択
    *   **構成:** `Cloud Build 構成ファイル (yaml または json)`
    *   **場所:** `リポジトリ` （`cloudbuild.yaml`のパスは `/cloudbuild.yaml`）
4.  「作成」をクリックしてトリガーを保存します。

これで、指定したブランチにコードがプッシュされるたびに、自動でテストとデプロイが実行されます。

## 2. ローカルでの開発とテスト

### 2.1. サーバーの起動

ローカルでサーバーを起動してテストする場合、以下のコマンドで認証情報を設定します。
```bash
gcloud auth application-default login
```
その後、bash互換シェルで起動スクリプトを実行します。
```bash
./start_local.sh
```

### 2.2. テストの実行

単体テストは以下のコマンドで実行できます。
```bash
pytest tests/
```

## 3. 手動でのデプロイ (任意)

CI/CDを使わず手動でデプロイする場合は、以下のコマンドを実行します。

```bash
# ビルド
gcloud builds submit --config cloudbuild.yaml .

# もしくは個別に実行
# gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/jmap-app
# gcloud run deploy jmap-app --image gcr.io/$(gcloud config get-value project)/jmap-app ...
```