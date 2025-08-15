#!/bin/sh
set -eu

# exec を使ってGunicornを起動します。
# これにより、GunicornがコンテナのPID 1プロセスとなり、
# Cloud RunからのSIGTERMのようなシグナルを直接受け取ることができます。
# これにより、安全なグレースフルシャットダウンが可能になります。
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 8 --timeout 0 --log-level info "main:app"
