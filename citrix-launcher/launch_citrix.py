#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
標準仮想PC（Citrix）自動起動ツール
=====================================

Safari/Edge で rpc.soka.jp（Citrix StoreFront）を開き、
お気に入りの「標準仮想PC」をクリック → ダウンロードされた .ica を開く →
Windows ログイン画面でパスワードを自動入力 …… という一連の操作を自動化します。

特徴:
  * 画面の解像度や位置の違いに強い設計（座標ベタ打ちをしない）
      - タイルのクリック : 画像認識（テンプレートマッチング）
      - .ica を開く      : ダウンロードフォルダの「最新の .ica」を自動オープン
      - パスワード入力   : キーストローク送信（OSの資格情報ストアから取得）
  * パスワードは Mac=キーチェーン / Windows=資格情報マネージャー に安全に保存
    （keyring ライブラリ経由。スクリプトには一切書きません）

初回は `setup_tool.py`（初期設定）を実行してください。
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# --- 依存ライブラリの読み込み（無ければ分かりやすく案内） -------------------
try:
    import pyautogui
except Exception as exc:  # noqa: BLE001
    print("必要なライブラリ pyautogui が見つかりません。")
    print("初期設定（初期設定.command / 初期設定.bat）を先に実行してください。")
    print(f"詳細: {exc}")
    sys.exit(1)

try:
    import keyring
except Exception as exc:  # noqa: BLE001
    print("必要なライブラリ keyring が見つかりません。")
    print("初期設定を先に実行してください。")
    print(f"詳細: {exc}")
    sys.exit(1)


HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
TEMPLATES_DIR = HERE / "templates"


# --- ユーティリティ ----------------------------------------------------------
def log(msg: str) -> None:
    """時刻つきでログ出力。"""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_config() -> dict:
    """config.json を読み込む。"""
    if not CONFIG_PATH.exists():
        log(f"設定ファイルが見つかりません: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def downloads_dir(cfg: dict) -> Path:
    """ダウンロードフォルダを決定する。"""
    configured = cfg.get("downloads_dir", "").strip()
    if configured:
        return Path(os.path.expanduser(configured))
    return Path.home() / "Downloads"


def open_file(path: str) -> None:
    """OSの既定アプリでファイルを開く（.ica → Citrix Workspace）。"""
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606
    else:
        subprocess.run(["xdg-open", path], check=False)


def template_path(cfg: dict, key: str) -> Path | None:
    """テンプレート画像のパスを返す（存在しなければ None）。"""
    name = cfg.get("templates", {}).get(key, "")
    if not name:
        return None
    p = TEMPLATES_DIR / name
    return p if p.exists() else None


# --- 主要ステップ ------------------------------------------------------------
def get_credentials(cfg: dict) -> tuple[str, str]:
    """OSの資格情報ストアからユーザー名とパスワードを取得する。"""
    service = cfg["credential_service"]
    username = cfg.get("username", "").strip() or os.getlogin()
    password = keyring.get_password(service, username)
    if not password:
        log("パスワードが保存されていません。")
        log("先に「初期設定」を実行してパスワードを登録してください。")
        sys.exit(1)
    return username, password


def open_store(cfg: dict) -> None:
    """既定ブラウザで StoreFront を開く（既存のログインセッションを利用）。"""
    url = cfg["store_url"]
    log(f"ブラウザで StoreFront を開きます: {url}")
    webbrowser.open(url)
    time.sleep(cfg["timeouts"]["page_load"])


def click_tile(cfg: dict) -> bool:
    """「標準仮想PC」のタイルを画像認識でクリックする。"""
    tile = template_path(cfg, "tile")
    if tile is None:
        log("タイルのテンプレート画像が無いため、画像クリックをスキップします。")
        log("（初期設定でタイルのスクリーンショットを登録すると自動クリックできます）")
        log(f"手動で「{cfg['resource_name']}」をクリックしてください。")
        return False

    confidence = cfg.get("image_confidence", 0.8)
    deadline = time.time() + cfg["timeouts"]["tile_search"]
    log(f"画面から「{cfg['resource_name']}」のタイルを探しています…")
    while time.time() < deadline:
        try:
            loc = pyautogui.locateCenterOnScreen(str(tile), confidence=confidence)
        except Exception:  # noqa: BLE001  (画像未検出時に例外を出す版がある)
            loc = None
        if loc is not None:
            pyautogui.click(loc)
            log("タイルをクリックしました。")
            return True
        time.sleep(1)

    log("タイルが見つかりませんでした。")
    log("・ブラウザで rpc.soka.jp にログイン済みか")
    log("・タイルが画面に表示されているか")
    log("・テンプレート画像が現在の画面と一致しているか（初期設定で取り直し）")
    log("を確認してください。")
    return False


def wait_and_open_ica(cfg: dict, since_ts: float) -> bool:
    """ダウンロードフォルダに新しく現れた .ica を開く。"""
    folder = downloads_dir(cfg)
    pattern = str(folder / cfg.get("ica_glob", "*.ica"))
    deadline = time.time() + cfg["timeouts"]["ica_wait"]
    log(f"ダウンロードフォルダの新しい .ica を待っています: {folder}")
    while time.time() < deadline:
        candidates = [
            f for f in glob.glob(pattern)
            if os.path.getmtime(f) >= since_ts - 1.0
        ]
        if candidates:
            newest = max(candidates, key=os.path.getmtime)
            # 書き込み完了を待つ（サイズが安定するまで）
            time.sleep(1.0)
            log(f".ica を開きます: {os.path.basename(newest)}")
            open_file(newest)
            return True
        time.sleep(0.5)

    log(".ica ファイルが見つかりませんでした。タイルのクリックに失敗した可能性があります。")
    return False


def type_password(cfg: dict, password: str) -> None:
    """Windows ログイン画面が出たらパスワードを入力する。"""
    if not cfg.get("type_password", True):
        log("パスワード自動入力は無効です（設定: type_password=false）。")
        return

    lock = template_path(cfg, "lock")
    timeout = cfg["timeouts"]["lock_screen"]
    if lock is not None:
        confidence = cfg.get("image_confidence", 0.8)
        deadline = time.time() + timeout
        log("Windows ログイン画面の表示を待っています…")
        found = False
        while time.time() < deadline:
            try:
                loc = pyautogui.locateCenterOnScreen(str(lock), confidence=confidence)
            except Exception:  # noqa: BLE001
                loc = None
            if loc is not None:
                found = True
                pyautogui.click(loc)  # 入力欄付近をクリックしてフォーカス
                break
            time.sleep(1)
        if not found:
            log("ログイン画面を検出できませんでした。パスワード入力をスキップします。")
            return
    else:
        wait = cfg.get("lock_screen_pre_delay", 25)
        log(f"ログイン画面のテンプレートが無いため {wait} 秒待機します…")
        time.sleep(wait)
        # 画面中央をクリックしてフォーカスを当てる
        w, h = pyautogui.size()
        pyautogui.click(w // 2, h // 2)

    time.sleep(1.0)
    log("パスワードを入力します。")
    pyautogui.write(password, interval=0.05)
    if cfg.get("press_enter_after_password", True):
        pyautogui.press("enter")
    log("ログイン操作を送信しました。")


# --- メイン ------------------------------------------------------------------
def main() -> None:
    cfg = load_config()

    # macOS では誤操作防止のフェイルセーフが有効（左上角にマウスで中断）
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3

    log("=== 標準仮想PC 自動起動 開始 ===")
    _username, password = get_credentials(cfg)

    since_ts = time.time()
    open_store(cfg)

    clicked = click_tile(cfg)
    if not clicked:
        # 自動クリックできなくても、手動クリック後の .ica は拾えるよう続行
        log("手動でタイルをクリックしてください。続けて .ica を監視します。")

    if not wait_and_open_ica(cfg, since_ts):
        log("=== 中断しました ===")
        sys.exit(1)

    type_password(cfg, password)
    log("=== 完了。仮想PCのデスクトップが表示されるまでお待ちください ===")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断しました。")
        sys.exit(130)
