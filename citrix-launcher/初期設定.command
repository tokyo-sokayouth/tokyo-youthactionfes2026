#!/bin/bash
# 標準仮想PC 自動起動  初期設定（Mac用）— 最初に一度だけ実行してください
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "Python3 が見つかりません。https://www.python.org からインストールしてください。"
  read -n 1 -s -r -p "何かキーを押すと閉じます…"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "初回セットアップ中です（少し時間がかかります）…"
  "$PY" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip >/dev/null
  ./.venv/bin/python -m pip install -r requirements.txt
fi

./.venv/bin/python setup_tool.py
echo ""
read -n 1 -s -r -p "設定が終わりました。何かキーを押すと閉じます…"
