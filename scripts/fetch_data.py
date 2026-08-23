#!/usr/bin/env python3
"""
松山市オープンデータ取得スクリプト
Usage: python3 scripts/fetch_data.py
出力: scripts/raw/ に各CSVを保存
"""

import os
import sys
import requests
import chardet

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(RAW_DIR, exist_ok=True)

SOURCES = [
    {
        "key": "evacuation",
        "url": "https://www.city.matsuyama.ehime.jp/shisei/opendata/metadata/hinanbasho.files/382019_evacuation_space.csv",
        "filename": "evacuation.csv",
        "desc": "緊急避難場所",
    },
    {
        "key": "aed",
        "url": "https://www.city.matsuyama.ehime.jp/shisei/opendata/metadata/aeditiran.files/382019_aed.csv",
        "filename": "aed.csv",
        "desc": "AED設置箇所",
    },
    {
        "key": "school",
        "url": "https://www.city.matsuyama.ehime.jp/shisei/opendata/metadata/e-gakkou.files/040128shisetsumei-ichijyouhou.csv",
        "filename": "school.csv",
        "desc": "学校施設座標",
    },
    {
        "key": "public_facility",
        "url": "https://www.city.matsuyama.ehime.jp/shisei/opendata/metadata/shisetsu.files/382019_public_facility.csv",
        "filename": "public_facility.csv",
        "desc": "公共施設一覧",
    },
]


def fetch_csv(url: str, filename: str, desc: str) -> bool:
    out_path = os.path.join(RAW_DIR, filename)
    if os.path.exists(out_path):
        print(f"  [SKIP] {desc} ({filename}) - already downloaded")
        return True

    print(f"  Fetching {desc} ...", end=" ", flush=True)
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "SafePin/1.0"})
        r.raise_for_status()

        detected = chardet.detect(r.content)
        enc = detected.get("encoding") or "utf-8"
        if enc.lower() in ("shift_jis", "shift-jis", "sjis"):
            enc = "cp932"

        with open(out_path, "wb") as f:
            f.write(r.content)

        print(f"OK ({len(r.content):,} bytes, detected {enc})")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def main():
    print("=== 松山市オープンデータ 取得 ===\n")
    ok_count = 0
    for src in SOURCES:
        if fetch_csv(src["url"], src["filename"], src["desc"]):
            ok_count += 1

    print(f"\n{ok_count}/{len(SOURCES)} ファイル取得完了")
    print(f"保存先: {RAW_DIR}")

    if ok_count < len(SOURCES):
        print("\n[注意] 取得に失敗したファイルは手動でダウンロードして scripts/raw/ に配置してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()
