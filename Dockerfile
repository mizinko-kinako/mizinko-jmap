# 1. ベースイメージの選択
# 公式のPythonイメージをベースとして使用します
FROM python:3.12-slim

# 2. 環境変数の設定
# Pythonのログがバッファリングされず、すぐに出力されるようにします
ENV PYTHONUNBUFFERED=1
# Gunicornがリッスンするポートを設定します（Cloud Runが自動的に設定するPORT環境変数を参照）
ENV PORT 8080

# 3. 作業ディレクトリの作成と設定
WORKDIR /app

# 4. 依存関係のインストール
# requirements.txtを先にコピーし、キャッシュを活用してビルドを高速化します
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリケーションコードと起動スクリプトのコピー
# srcディレクトリの中身と起動スクリプトをコンテナの作業ディレクトリにコピーします
COPY src/ .
COPY start.sh .

# 6. 起動スクリプトに実行権限を付与
RUN chmod +x ./start.sh

# 7. ポートの公開
# コンテナがリッスンするポートを公開します
EXPOSE 8080

# 8. コンテナ起動コマンドの設定
# 作成した起動スクリプトを実行します
CMD ["./start.sh"]
