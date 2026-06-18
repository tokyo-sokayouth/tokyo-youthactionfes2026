@echo off
REM 標準仮想PC 自動起動（Windows用）— ダブルクリックで実行してください
chcp 65001 >nul
cd /d "%~dp0"

REM Python を探す（py 優先、無ければ python）
where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

%PY% --version >nul 2>nul
if not %errorlevel%==0 (
  echo Python が見つかりません。https://www.python.org からインストールしてください。
  echo インストール時は「Add Python to PATH」にチェックを入れてください。
  pause
  exit /b 1
)

REM 初回のみ仮想環境を作成し、依存ライブラリを導入
if not exist ".venv" (
  echo 初回セットアップ中です（少し時間がかかります）…
  %PY% -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

".venv\Scripts\python.exe" launch_citrix.py
if not %errorlevel%==0 (
  echo.
  echo エラーが発生しました（コード: %errorlevel%）。
  pause
)
