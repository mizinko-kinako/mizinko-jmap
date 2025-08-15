#!/bin/bash
#
# ローカル開発環境でWebサーバーを起動するスクリプト
#

# 仮想環境(jmap)のPythonインタープリタを使って、src/main.pyを実行
# python-dotenvライブラリが自動で.envファイルを読み込みます
echo "Starting development server..."
./jmap/Scripts/python.exe src/main.py
