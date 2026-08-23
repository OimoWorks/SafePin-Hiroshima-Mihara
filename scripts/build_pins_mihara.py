#!/usr/bin/env python3
"""
三原市オープンデータ / 国土地理院データから pins-data.json を生成するスクリプト
Usage: python3 scripts/build_pins_mihara.py

前提: scripts/raw/ に以下が存在すること
  - evacuation_sites.csv  (指定緊急避難場所 / 国土地理院 34204_2.csv)
  - shelters.csv          (指定避難所 / 国土地理院 34204_1.csv)
  - aed.csv               (AED設置箇所一覧 / 三原市オープンデータカタログ 342041_aed.csv)
  - public_toilet.csv     (公衆トイレ一覧 / 三原市オープンデータカタログ 342041_public_toilet.csv)

出力: lib/pins-data.json
"""

import csv
import io
import json
import os

import chardet

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "lib", "pins-data.json")
GENERATED_AT = "2026-08-21"


def read_csv(filename: str) -> list[dict]:
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        print(f"  [WARN] {filename} が見つかりません")
        return []
    raw = open(path, "rb").read()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    if enc.lower() in ("shift_jis", "shift-jis", "sjis"):
        enc = "cp932"
    text = raw.decode(enc, errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def safe_float(v) -> float | None:
    try:
        return round(float(str(v).strip()), 6)
    except (ValueError, TypeError):
        return None


# ── 指定緊急避難場所（国土地理院） ─────────────────────────────

_HAZARD_COLS = [
    ("洪水", "洪水"),
    ("崖崩れ、土石流及び地滑り", "土砂災害"),
    ("高潮", "高潮"),
    ("地震", "地震"),
    ("津波", "津波"),
    ("大規模な火事", "大規模火災"),
    ("内水氾濫", "内水氾濫"),
    ("火山現象", "火山現象"),
]


def parse_evacuation_sites(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        name = (row.get("施設・場所名") or "").strip()
        address = (row.get("住所") or "").strip()
        lat = safe_float(row.get("緯度"))
        lng = safe_float(row.get("経度"))
        if not name or lat is None or lng is None:
            continue
        hazards = [label for col, label in _HAZARD_COLS if (row.get(col) or "").strip() == "1"]
        notes = f"対応災害: {'・'.join(hazards)}" if hazards else "対応災害情報なし"
        pins.append({
            "id": f"evac-{i + 1}",
            "category": "evacuation_site",
            "name": name,
            "address": address,
            "lat": lat,
            "lng": lng,
            "detail": {"capacity": 0, "notes": notes},
            "updatedAt": GENERATED_AT,
        })
    return pins


# ── 指定避難所（国土地理院） ────────────────────────────────────

def parse_shelters(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        name = (row.get("施設・場所名") or "").strip()
        address = (row.get("住所") or "").strip()
        lat = safe_float(row.get("緯度"))
        lng = safe_float(row.get("経度"))
        if not name or lat is None or lng is None:
            continue
        accept = (row.get("受入対象者") or "").strip()
        remarks = (row.get("備考") or "").strip()
        notes_parts = []
        if accept:
            notes_parts.append(f"受入対象: {accept}")
        if remarks:
            notes_parts.append(remarks)
        notes = "　".join(notes_parts) if notes_parts else "指定避難所"
        pins.append({
            "id": f"shelter-{i + 1}",
            "category": "shelter",
            "name": name,
            "address": address,
            "lat": lat,
            "lng": lng,
            "detail": {"capacity": 0, "notes": notes},
            "updatedAt": GENERATED_AT,
        })
    return pins


# ── AED（三原市オープンデータ） ─────────────────────────────────

def parse_aed(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        name = (row.get("名称") or "").strip()
        addr = (row.get("所在地_連結表記") or "").strip()
        lat = safe_float(row.get("緯度"))
        lng = safe_float(row.get("経度"))
        if not name or lat is None or lng is None:
            continue
        position = (row.get("設置位置") or "").strip()
        hours = ""
        start, end, days = (row.get("開始時間") or "").strip(), (row.get("終了時間") or "").strip(), (row.get("利用可能曜日") or "").strip()
        if start and end:
            hours = f"利用可能: {days} {start}〜{end}"
        notes_parts = [p for p in [position, hours] if p]
        pins.append({
            "id": f"aed-{i + 1}",
            "category": "aed",
            "name": name,
            "address": addr,
            "lat": lat,
            "lng": lng,
            "detail": {
                "facilityName": name,
                "notes": "　".join(notes_parts) if notes_parts else "設置箇所",
            },
            "updatedAt": GENERATED_AT,
        })
    return pins


# ── 公衆トイレ（三原市オープンデータ） ───────────────────────────
# 注: 松山市版の「マンホールトイレ」(災害時設置の応急トイレ)とは異なり、
#     三原市版は常設の公衆トイレデータを使用。ラベルもtypes.tsで区別する。

def parse_toilets(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        name = (row.get("名称") or "").strip()
        addr = (row.get("所在地_連結表記") or "").strip()
        lat = safe_float(row.get("緯度"))
        lng = safe_float(row.get("経度"))
        if not name or lat is None or lng is None:
            continue

        def _cnt(col):
            try:
                return int(str(row.get(col) or "0").strip() or 0)
            except ValueError:
                return 0

        male = _cnt("男性トイレ総数")
        female = _cnt("女性トイレ総数")
        unisex = _cnt("男女共用トイレ総数")
        total = male + female + unisex
        barrier_free = (row.get("車椅子使用者用トイレ有無") or "").strip() == "有"
        baby = (row.get("乳幼児用設備設置トイレ有無") or "").strip() == "有"
        tags = []
        if barrier_free:
            tags.append("車椅子対応あり")
        if baby:
            tags.append("乳幼児設備あり")
        notes = "　".join(tags) if tags else "公衆トイレ"
        pins.append({
            "id": f"toilet-{i + 1}",
            "category": "toilet",
            "name": name,
            "address": addr,
            "lat": lat,
            "lng": lng,
            "detail": {"capacity": total, "notes": notes},
            "updatedAt": GENERATED_AT,
        })
    return pins


# ── メイン ────────────────────────────────────────────────────

def main():
    print("=== SafePin三原版 ピンデータ生成 ===\n")

    all_pins: list[dict] = []

    evac_rows = read_csv("evacuation_sites.csv")
    evac_pins = parse_evacuation_sites(evac_rows)
    all_pins.extend(evac_pins)
    print(f"緊急避難場所: {len(evac_pins)}件")

    shelter_rows = read_csv("shelters.csv")
    shelter_pins = parse_shelters(shelter_rows)
    all_pins.extend(shelter_pins)
    print(f"指定避難所: {len(shelter_pins)}件")

    aed_rows = read_csv("aed.csv")
    aed_pins = parse_aed(aed_rows)
    all_pins.extend(aed_pins)
    print(f"AED: {len(aed_pins)}件")

    toilet_rows = read_csv("public_toilet.csv")
    toilet_pins = parse_toilets(toilet_rows)
    all_pins.extend(toilet_pins)
    print(f"公衆トイレ: {len(toilet_pins)}件")

    print(f"\n合計: {len(all_pins)}件")
    print("[INFO] 応急給水栓(water)データは三原市オープンデータに未整備のため今回は未収録")

    out = {
        "pins": all_pins,
        "skipped": [],
        "generatedAt": GENERATED_AT,
        "source": "三原市オープンデータカタログ / 国土地理院 指定緊急避難場所・指定避難所データ (CC BY 4.0)",
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n出力完了: {OUT_PATH}")


if __name__ == "__main__":
    main()
