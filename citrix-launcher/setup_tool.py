#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初期設定ツール
================

配布先の方が「最初に一度だけ」実行する設定ウィザードです。

  1. Windows ログイン用のユーザー名・パスワードを
     OSの資格情報ストア（Mac=キーチェーン / Windows=資格情報マネージャー）に保存
  2. 「標準仮想PC」タイルの画像、（任意で）ログイン画面の画像の登録方法を案内
  3. 権限まわり（Mac のアクセシビリティ/画面収録）の確認方法を案内

パスワードはこのツールのファイルやリポジトリには一切書き込まれません。
"""

from __future__ import annotations

import getpass
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import keyring
except Exception as exc:  # noqa: BLE001
    print("必要なライブラリ keyring が見つかりません。")
    print("起動用ファイル（初期設定.command / 初期設定.bat）から実行してください。")
    print(f"詳細: {exc}")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
TEMPLATES_DIR = HERE / "templates"


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def open_folder(path: Path) -> None:
    """フォルダをFinder/エクスプローラーで開く。"""
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def register_credentials(cfg: dict) -> None:
    print("\n--- 1. ログイン情報の登録 -------------------------------------")
    service = cfg["credential_service"]
    default_user = cfg.get("username", "").strip() or os.getlogin()
    username = input(f"ユーザー名 [{default_user}]: ").strip() or default_user

    existing = keyring.get_password(service, username)
    if existing:
        ans = input("既にパスワードが登録されています。更新しますか? [y/N]: ").strip().lower()
        if ans != "y":
            print("パスワードはそのままにします。")
            return

    while True:
        pw1 = getpass.getpass("パスワード（入力は画面に表示されません）: ")
        pw2 = getpass.getpass("もう一度パスワード: ")
        if not pw1:
            print("空のパスワードは登録できません。")
            continue
        if pw1 != pw2:
            print("一致しません。もう一度入力してください。")
            continue
        break

    keyring.set_password(service, username, pw1)
    print(f"✓ パスワードをOSの資格情報ストアに保存しました（サービス名: {service}）。")
    print("  ※ このファイルやリポジトリには保存されていません。")


def guide_templates(cfg: dict) -> None:
    print("\n--- 2. 画像（テンプレート）の登録 -----------------------------")
    tiles = cfg.get("templates", {})
    tile_name = tiles.get("tile", "tile.png")
    lock_name = tiles.get("lock", "lock.png")
    print("自動クリックには、お使いの画面のスクリーンショットが必要です。")
    print("（画面の見た目は人によって違うため、各自で1回だけ撮影します）\n")
    if sys.platform == "darwin":
        print("■ Mac での撮影方法:")
        print("  1) Safari で rpc.soka.jp を開き「標準仮想PC」タイルを表示")
        print("  2) Command + Shift + 4 を押し、タイル部分だけを範囲選択して撮影")
        print("  3) デスクトップにできた画像を、後で開くフォルダへ入れて")
        print(f"     ファイル名を「{tile_name}」に変更")
    else:
        print("■ Windows での撮影方法:")
        print("  1) ブラウザで rpc.soka.jp を開き「標準仮想PC」タイルを表示")
        print("  2) 「切り取り & スケッチ（Snipping Tool）」でタイル部分だけを撮影")
        print(f"  3) 後で開くフォルダに「{tile_name}」という名前で保存")
    print(f"\n（任意）ログイン画面も同様に撮影して「{lock_name}」として保存すると、")
    print("  パスワード入力のタイミングがより正確になります。")
    print("  撮影しない場合は config.json の lock_screen_pre_delay 秒だけ待ってから入力します。")

    ans = input("\nテンプレート用フォルダを今すぐ開きますか? [Y/n]: ").strip().lower()
    if ans in ("", "y"):
        open_folder(TEMPLATES_DIR)
        print(f"→ このフォルダに画像を入れてください: {TEMPLATES_DIR}")


def guide_permissions() -> None:
    if sys.platform != "darwin":
        return
    print("\n--- 3. Mac の権限設定（重要）---------------------------------")
    print("自動クリック・キーボード入力には、以下2つの許可が必要です。")
    print("  システム設定 → プライバシーとセキュリティ → ")
    print("    ・アクセシビリティ   … 起動に使うアプリ（ターミナル等）を追加してオン")
    print("    ・画面収録           … 同上（画像認識のため画面の読み取りが必要）")
    print("  ※ 設定後はアプリを再起動してください。")


def main() -> None:
    cfg = load_config()
    print("==============================================")
    print(" 標準仮想PC 自動起動ツール  初期設定")
    print("==============================================")
    register_credentials(cfg)
    guide_templates(cfg)
    guide_permissions()
    print("\nすべて完了したら「仮想PC起動」を実行してください。お疲れさまでした！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断しました。")
        sys.exit(130)
