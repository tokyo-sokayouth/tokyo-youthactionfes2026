#!/bin/bash
# 標準仮想PC 自動起動（Mac用）— ダブルクリックで実行してください
set -e
cd "$(dirname "$0")"

# Python3 を探す
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "Python3 が見つかりません。https://www.python.org からインストールしてください。"
  read -n 1 -s -r -p "何かキーを押すと閉じます…"
  exit 1
fi

# 初回のみ仮想環境を作成し、依存ライブラリを導入
if [ ! -d ".venv" ]; then
  echo "初回セットアップ中です（少し時間がかかります）…"
  "$PY" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip >/dev/null
  ./.venv/bin/python -m pip install -r requirements.txt
fi

./.venv/bin/python launch_citrix.py
status=$?
if [ $status -ne 0 ]; then
  echo ""
  echo "エラーが発生しました（コード: $status）。"
  read -n 1 -s -r -p "何かキーを押すと閉じます…"
fi
