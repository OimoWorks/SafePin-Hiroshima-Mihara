#!/usr/bin/env python3
"""
松山市オープンデータから pins-data.json を生成するスクリプト
Usage: python3 scripts/build_pins.py

前提: scripts/raw/ に以下が存在すること
  必須:
  - evacuation.csv       (緊急避難場所)
  - aed.csv              (AED)
  - school.csv           (学校座標)
  - public_facility.csv  (公共施設一覧)
  任意（あると座標解決率が上がる）
  - shelter.csv          (指定避難所 - OCR等で変換済みのもの)
  - manhole.csv          (マンホールトイレ一覧 - 手動整備)
  - P20-12_38.xml        (国土数値情報「避難施設」愛媛県版)
  - shelter_overrides.csv (手動座標修正ファイル: 施設名,住所,lat,lng)

オプション環境変数:
  GOOGLE_MAPS_API_KEY    (Google Geocoding API キー)
                         設定しない場合、このステップはスキップされる

出力: lib/pins-data.json
  - "pins": [...]        通常ピンデータ
  - "skipped": [...]     座標解決できなかった指定避難所の一覧
"""

import csv
import io
import json
import os
import re
import time
import unicodedata
import xml.etree.ElementTree as ET

import chardet
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(SCRIPT_DIR, "raw")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "lib", "pins-data.json")


# ── ユーティリティ ────────────────────────────────────────────

def read_csv(filename: str) -> list[dict]:
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        return []
    raw = open(path, "rb").read()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    if enc.lower() in ("shift_jis", "shift-jis", "sjis"):
        enc = "cp932"
    text = raw.decode(enc, errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s).replace(" ", "").replace("　", "")


def safe_float(v: str) -> float | None:
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None


# ── 座標ソース 0: shelter_overrides.csv（手動修正・最優先） ──────────────

def build_overrides_index(
    rows: list[dict],
) -> tuple[dict[tuple[str, str], tuple[float, float]], dict[str, tuple[float, float]]]:
    """
    shelter_overrides.csv の内容を2つのインデックスに変換する。
    列名の揺れに対応: 施設名/名称、lat/緯度、lng/経度

    戻り値:
      addr_index: {(正規化施設名, 正規化住所ヒント): (lat, lng)}
                  「住所」列が非空の行。shelter の住所への部分一致で照合。
      name_index: {正規化施設名: (lat, lng)}
                  全エントリを登録（同名施設のアドレスマッチが失敗した際のフォールバック）。
    """
    addr_index: dict[tuple[str, str], tuple[float, float]] = {}
    name_index: dict[str, tuple[float, float]] = {}
    for row in rows:
        # 列名の揺れに対応: 施設名/名称、lat/緯度、lng/経度
        name = normalize((row.get("施設名") or row.get("名称") or "").strip())
        addr = normalize((row.get("住所") or "").strip())
        lat = safe_float(row.get("lat") or row.get("緯度") or "")
        lng = safe_float(row.get("lng") or row.get("経度") or "")
        if not name or not lat or not lng:
            continue
        # 全エントリを name_index に登録（名前だけで一意に特定できる65件のフォールバック）
        name_index[name] = (lat, lng)
        if addr:
            # 住所付きエントリは addr_index にも登録（同名施設の住所による区別）
            addr_index[(name, addr)] = (lat, lng)
    return addr_index, name_index


def lookup_override(
    addr_index: dict[tuple[str, str], tuple[float, float]],
    name_index: dict[str, tuple[float, float]],
    name: str,
    address: str,
) -> tuple[float, float] | None:
    """
    overrides インデックスから座標を検索する。
    1. 住所ヒント付き: 部分一致（双方向）で同名施設を区別
    2. 名前のみ: name_index に名前があれば返す
    """
    key_name = normalize(name)
    key_addr = normalize(address)
    for (n, a), coords in addr_index.items():
        # 双方向部分一致: override住所が長くても短くても対応
        if n == key_name and (a in key_addr or key_addr in a):
            return coords
    return name_index.get(key_name)


# ── 座標ソース 1-2: 学校・公共施設インデックス ────────────────────────

def build_school_index(rows: list[dict]) -> dict[str, tuple[float, float]]:
    index = {}
    for row in rows:
        biko = normalize(row.get("備考", "") or "")
        if "廃校" in biko or "休校" in biko:
            continue
        name_raw = (row.get("名称") or row.get("施設名") or "").strip()
        name = normalize(name_raw)
        if not name:
            continue
        lat = safe_float(row.get("Y") or row.get("緯度") or "")
        lng = safe_float(row.get("X") or row.get("経度") or "")
        if lat and lng and abs(lat) > 1 and abs(lng) > 1:
            index[name] = (lat, lng)
    return index


def lookup_school(school_index: dict, name: str) -> tuple[float, float] | None:
    key = normalize(name)
    if key in school_index:
        return school_index[key]
    for k, v in school_index.items():
        if key in k and len(key) >= len(k) * 0.7:
            return v
        if k in key and len(k) >= len(key) * 0.7:
            return v
    return None


def build_facility_index(rows: list[dict]) -> dict[str, tuple[float, float]]:
    index = {}
    for row in rows:
        name_raw = (row.get("名称") or "").strip()
        name_clean = re.sub(r'[（(][^）)]*[）)]', '', name_raw).strip()
        name = normalize(name_clean)
        if not name:
            continue
        lat = safe_float(row.get("緯度") or "")
        lng = safe_float(row.get("経度") or "")
        if lat and lng and abs(lat) > 1 and abs(lng) > 1:
            index[name] = (lat, lng)
    return index


_FACILITY_VARIANTS: list[tuple[str, str]] = [
    ("分館", "集会所"),
    ("集会所", "分館"),
    ("分校", "小学校"),
    ("小学校", "分校"),
    ("出張所", "支所"),
    ("支所", "出張所"),
]


def _facility_variants(key: str) -> list[str]:
    variants = []
    for src, dst in _FACILITY_VARIANTS:
        if src in key:
            variants.append(key.replace(src, dst))
    return variants


def lookup_facility(facility_index: dict, name: str) -> tuple[float, float] | None:
    key = normalize(name)
    if key in facility_index:
        return facility_index[key]
    for variant in _facility_variants(key):
        if variant in facility_index:
            return facility_index[variant]
    return None


# ── 座標ソース 3: 国土数値情報 P20「避難施設」 XML ─────────────────

_P20_NS = {
    'gml':   'http://www.opengis.net/gml/3.2',
    'ksj':   'http://nlftp.mlit.go.jp/ksj/schemas/ksj-app',
    'xlink': 'http://www.w3.org/1999/xlink',
}
_MATSUYAMA_CODE = '38201'


def parse_p20_xml(xml_path: str) -> list[dict]:
    """
    国土数値情報P20 XMLから松山市（adminstrativeAreaCode=38201）の
    避難施設レコードを抽出して返す。
    各レコード: {"name": str, "address": str, "lat": float, "lng": float}
    """
    try:
        tree = ET.parse(xml_path)
    except Exception as e:
        print(f"  [WARN] P20 XMLパース失敗: {e}")
        return []

    root = tree.getroot()

    # gml:Point id → (lat, lng)
    points: dict[str, tuple[float, float]] = {}
    for pt in root.findall('.//gml:Point', _P20_NS):
        pt_id = pt.get('{http://www.opengis.net/gml/3.2}id', '')
        pos = pt.find('gml:pos', _P20_NS)
        if pos is not None and pos.text:
            parts = pos.text.strip().split()
            if len(parts) == 2:
                lat, lng = safe_float(parts[0]), safe_float(parts[1])
                if lat and lng:
                    points[pt_id] = (lat, lng)

    features = []
    for ef in root.findall('.//ksj:EvacuationFacilities', _P20_NS):
        # KSJデータの表記ゆれ対応（administrativeAreaCode vs adminstrativeAreaCode）
        area_code = ''
        for tag in ('ksj:adminstrativeAreaCode', 'ksj:administrativeAreaCode'):
            el = ef.find(tag, _P20_NS)
            if el is not None:
                area_code = (el.text or '').strip()
                break
        if area_code != _MATSUYAMA_CODE:
            continue

        name_el = ef.find('ksj:name', _P20_NS)
        addr_el = ef.find('ksj:address', _P20_NS)
        pos_el  = ef.find('ksj:position', _P20_NS)

        name = (name_el.text or '').strip() if name_el is not None else ''
        addr = (addr_el.text or '').strip() if addr_el is not None else ''
        if not name:
            continue

        pt_ref = ''
        if pos_el is not None:
            href = pos_el.get('{http://www.w3.org/1999/xlink}href', '')
            pt_ref = href.lstrip('#')

        coords = points.get(pt_ref)
        if not coords:
            continue

        features.append({'name': name, 'address': addr, 'lat': coords[0], 'lng': coords[1]})

    return features


def build_p20_index(features: list[dict]) -> dict[str, tuple[float, float]]:
    index = {}
    for f in features:
        name = normalize(f['name'])
        if name:
            index[name] = (f['lat'], f['lng'])
    return index


def lookup_p20(p20_index: dict, name: str) -> tuple[float, float] | None:
    """
    P20インデックスで完全一致→部分一致（長さ 70%ガード付き）の順で検索。
    """
    key = normalize(name)
    if key in p20_index:
        return p20_index[key]
    for variant in _facility_variants(key):
        if variant in p20_index:
            return p20_index[variant]
    for k, v in p20_index.items():
        if key in k and len(key) >= len(k) * 0.7:
            return v
        if k in key and len(k) >= len(key) * 0.7:
            return v
    return None


# ── 座標ソース 4: Google Geocoding API ────────────────────────────────

_GOOGLE_ACCEPTED_TYPES = {'street_address', 'premise', 'subpremise'}
_GOOGLE_ACCEPTED_LOCATION_TYPES = {'ROOFTOP', 'RANGE_INTERPOLATED'}

_google_cache: dict[str, tuple[float, float] | None] = {}


def geocode_google(address: str, api_key: str) -> tuple[float, float] | None:
    """
    Google Geocoding APIで住所→座標変換。
    typesまたはlocation_typeで精度フィルタリングを行い、
    市区町村レベル以上の粗い結果は不採用にする。
    """
    if address in _google_cache:
        return _google_cache[address]

    full_address = address if re.match(r'^(北海道|.+[都道府県])', address) else f'愛媛県{address}'

    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    result = None
    try:
        r = requests.get(
            url,
            params={'address': full_address, 'key': api_key, 'language': 'ja'},
            timeout=10,
        )
        data = r.json()
        if data.get('status') == 'OK' and data.get('results'):
            res = data['results'][0]
            types = set(res.get('types', []))
            location_type = res.get('geometry', {}).get('location_type', '')
            if _GOOGLE_ACCEPTED_TYPES & types or location_type in _GOOGLE_ACCEPTED_LOCATION_TYPES:
                loc = res['geometry']['location']
                result = (loc['lat'], loc['lng'])
            else:
                print(f"    [Google SKIP] types={sorted(types)} location_type={location_type!r} → 精度不足")
        elif data.get('status') not in ('OK', 'ZERO_RESULTS'):
            print(f"    [Google WARN] status={data.get('status')!r}")
    except Exception as e:
        print(f"    [Google ERR] {e}")

    _google_cache[address] = result
    time.sleep(0.2)
    return result


# ── ピン生成：指定避難所 ─────────────────────────────────────────────

def parse_shelter_csv(
    rows: list[dict],
    overrides_addr_index: dict[tuple[str, str], tuple[float, float]],
    overrides_name_index: dict[str, tuple[float, float]],
    school_index: dict,
    facility_index: dict,
    p20_index: dict,
    google_api_key: str | None,
) -> tuple[list[dict], list[dict]]:
    """
    指定避難所CSVを処理し、(pins, skipped) のタプルを返す。

    座標解決の優先順位:
      0. shelter_overrides.csv（手動修正・最優先）
         0a. 名前＋住所ヒントで一致（同名施設の区別）
         0b. 名前のみで一致
      1. CSV自身の緯度経度
      2. 学校名マッチング (lookup_school)
      3. 公共施設一覧マッチング (lookup_facility)
      4. 国土数値情報P20マッチング (lookup_p20)
      5. Google Geocoding API（APIキー設定時のみ）
      6. スキップ → skippedリストに追加
    """
    pins: list[dict] = []
    skipped: list[dict] = []

    for i, row in enumerate(rows):
        name = (row.get("施設名") or "").strip()
        address = (row.get("住所") or "").strip()
        if not name:
            continue

        lat: float | None = None
        lng: float | None = None
        source = ''

        # ── ステップ 0: overrides ───────────────────────────────────────
        coords = lookup_override(overrides_addr_index, overrides_name_index, name, address)
        if coords:
            lat, lng = coords
            source = 'overrides'

        # ── ステップ 1: CSV自身の座標 ─────────────────────────────────
        if not lat or not lng:
            lat = safe_float(row.get("緯度") or row.get("Y") or "")
            lng = safe_float(row.get("経度") or row.get("X") or "")
            if lat and lng:
                source = 'csv'

        # ── ステップ 2: 学校名マッチング ──────────────────────────────
        if not lat or not lng:
            coords = lookup_school(school_index, name)
            if coords:
                lat, lng = coords
                source = 'school'

        # ── ステップ 3: 公共施設一覧マッチング ───────────────────────
        if not lat or not lng:
            coords = lookup_facility(facility_index, name)
            if coords:
                lat, lng = coords
                source = 'facility'

        # ── ステップ 4: 国土数値情報P20マッチング ─────────────────────
        if not lat or not lng:
            coords = lookup_p20(p20_index, name)
            if coords:
                lat, lng = coords
                source = 'p20'

        # ── ステップ 5: Google Geocoding ───────────────────────────────
        if not lat or not lng:
            if google_api_key and address:
                print(f"  [Google] {name}...", end=" ", flush=True)
                coords = geocode_google(address, google_api_key)
                if coords:
                    lat, lng = coords
                    source = 'google'
                    print("OK")
                else:
                    print("FAIL")

        # ── ステップ 6: スキップ ───────────────────────────────────────────
        if not lat or not lng:
            print(f"  [SKIP] {name} | {address}")
            skipped.append({"name": name, "address": address})
            continue

        disaster_keys = ["地震", "津波", "高潮", "洪水", "土砂"]
        applicable = [k for k in disaster_keys if str(row.get(k) or "").strip() in ("○", "〇", "△", "1")]
        notes = ("対応: " + "・".join(applicable)) if applicable else "指定避難所"

        pins.append({
            "id": f"shelter-{i + 1}",
            "category": "shelter",
            "name": name,
            "address": address,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "detail": {"capacity": 0, "notes": notes},
            "updatedAt": "2024-04-01",
            "_src": source,
        })

    return pins, skipped


# ── ピン生成：緊急避難場所 ─────────────────────────────────────────────

def parse_evacuation(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        lat = safe_float(row.get("緯度") or row.get("Y") or "")
        lng = safe_float(row.get("経度") or row.get("X") or "")
        if not lat or not lng:
            continue
        name = (row.get("名称") or "").strip()
        address = (row.get("所在地_連結表記") or row.get("住所") or "").strip()
        capacity_raw = row.get("想定収容人数") or ""
        try:
            capacity = int(re.sub(r"[^\d]", "", capacity_raw)) if capacity_raw.strip() else 0
        except ValueError:
            capacity = 0
        disaster_keys = ["洪水", "崖崩れ", "高潮", "地震", "津波", "大規模な火事", "内水汎濫", "火山現象"]
        applicable = [k for k in disaster_keys if str(row.get(f"災害種別_{k}") or row.get(k) or "").strip() == "1"]
        notes = "対応: " + "・".join(applicable) if applicable else "緊急避難場所"
        pins.append({
            "id": f"evac-{i + 1}", "category": "evacuation_site",
            "name": name, "address": address,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "detail": {"capacity": capacity, "notes": notes},
            "updatedAt": "2024-04-01",
        })
    return pins


# ── ピン生成：AED ──────────────────────────────────────────────────────

def parse_aed(rows: list[dict]) -> list[dict]:
    pins = []
    for i, row in enumerate(rows):
        lat = safe_float(row.get("緯度") or row.get("Y") or "")
        lng = safe_float(row.get("経度") or row.get("X") or "")
        if not lat or not lng:
            continue
        name = (row.get("名称") or "").strip()
        address = (row.get("所在地_連結表記") or row.get("住所") or "").strip()
        location = (row.get("設置位置") or "").strip()
        biko = (row.get("備考") or row.get("利用可能日時特記事項") or "").strip()
        notes_parts = [p for p in [location, biko] if p]
        notes = "、".join(notes_parts) if notes_parts else "AED設置箇所"
        pins.append({
            "id": f"aed-{i + 1}", "category": "aed",
            "name": f"AED（{name}）", "address": address,
            "lat": round(lat, 6), "lng": round(lng, 6),
            "detail": {"facilityName": name, "notes": notes},
            "updatedAt": "2024-04-01",
        })
    return pins


# ── ピン生成：マンホールトイレ・応急給水栓 ─────────────────────────────

def parse_manhole(rows: list[dict], school_index: dict, facility_index: dict) -> list[dict]:
    toilet_pins, water_pins = [], []
    if rows:
        print(f"  [DEBUG] manhole.csv 列名: {list(rows[0].keys())}")
    _AREA_PATTERN = re.compile(r'エリア|地区|地域|中心部')
    for i, row in enumerate(rows):
        school_name = (
            row.get("学校名") or row.get("施設名") or row.get("名称") or ""
        ).strip()
        school_name = re.sub(r'[（(]PDF[^）)]*[）)]', '', school_name).strip()
        if not school_name or _AREA_PATTERN.search(school_name):
            continue
        manhole_raw = row.get("マンホールトイレ基数") or row.get("基数") or "0"
        manhole_count = int(re.sub(r"[^\d]", "", str(manhole_raw)) or 0)
        water_raw = str(
            row.get("応急給水栓") or row.get("応急給水") or row.get("給水栓") or ""
        ).strip()
        has_water = water_raw in ("○", "〇", "有", "1", "true")
        year = (row.get("整備年度") or row.get("年度") or "").strip()
        coords = lookup_school(school_index, school_name)
        if not coords:
            coords = lookup_facility(facility_index, school_name)
        if not coords:
            print(f"  [WARN] 座標不明: {school_name}")
            continue
        lat, lng = coords
        if manhole_count > 0:
            toilet_pins.append({
                "id": f"toilet-{i + 1}", "category": "toilet",
                "name": f"マンホールトイレ（{school_name}）",
                "address": f"松山市 {school_name}",
                "lat": round(lat, 6), "lng": round(lng, 6),
                "detail": {"capacity": manhole_count * 5, "notes": f"{manhole_count}基設置（{year}年度整備）・災害時開放"},
                "updatedAt": "2024-04-01",
            })
        if has_water:
            water_pins.append({
                "id": f"water-{i + 1}", "category": "water",
                "name": f"応急給水栓（{school_name}）",
                "address": f"松山市 {school_name}",
                "lat": round(lat + 0.00005, 6), "lng": round(lng + 0.00005, 6),
                "detail": {"supplyAmount": "災害時供給", "notes": f"{school_name}構内・災害時開放（{year}年度整備）"},
                "updatedAt": "2024-04-01",
            })
    return toilet_pins + water_pins


# ── メイン ────────────────────────────────────────────────────────────────────────────────

def main():
    print("=== SafePin ピンデータ生成 ===\n")

    # ── インデックス構築 ──────────────────────────────────────────────────
    overrides_rows = read_csv("shelter_overrides.csv")
    overrides_addr_index, overrides_name_index = build_overrides_index(overrides_rows)
    total_overrides = len(overrides_addr_index) + len(overrides_name_index)
    if total_overrides:
        print(f"手動修正(overrides): {total_overrides}件 読み込み"
              f"（住所付き: {len(overrides_addr_index)}件、名前のみ: {len(overrides_name_index)}件）")

    school_rows = read_csv("school.csv")
    school_index = build_school_index(school_rows)
    print(f"学校座標: {len(school_index)}件 読み込み")

    facility_rows = read_csv("public_facility.csv")
    facility_index = build_facility_index(facility_rows)
    print(f"公共施設座標: {len(facility_index)}件 読み込み")

    p20_path = os.path.join(RAW_DIR, "P20-12_38.xml")
    if os.path.exists(p20_path):
        p20_features = parse_p20_xml(p20_path)
        p20_index = build_p20_index(p20_features)
        print(f"P20避難施設(松山市): {len(p20_index)}件 読み込み")
    else:
        p20_index = {}
        print("[SKIP] P20-12_38.xml なし（scripts/raw/ にコピーすると座標解決率が向上）")

    google_api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or None
    if google_api_key:
        print(f"Google Geocoding: 有効（キー末尾 ...{google_api_key[-4:]}）")
    else:
        print("[INFO] GOOGLE_MAPS_API_KEY 未設定 → Google Geocodingをスキップ")

    print()

    # ── ピン生成 ─────────────────────────────────────────────────────
    all_pins: list[dict] = []
    all_skipped: list[dict] = []

    evac_rows = read_csv("evacuation.csv")
    if evac_rows:
        evac_pins = parse_evacuation(evac_rows)
        all_pins.extend(evac_pins)
        print(f"緊急避難場所: {len(evac_pins)}件")
    else:
        print("[WARN] evacuation.csv が見つかりません")

    shelter_rows = read_csv("shelter.csv")
    if shelter_rows:
        shelter_pins, skipped = parse_shelter_csv(
            shelter_rows, overrides_addr_index, overrides_name_index,
            school_index, facility_index, p20_index, google_api_key
        )
        all_pins.extend(shelter_pins)
        all_skipped.extend(skipped)
        src_counts: dict[str, int] = {}
        for p in shelter_pins:
            src_counts[p.get("_src", "?")] = src_counts.get(p.get("_src", "?"), 0) + 1
        print(f"指定避難所: {len(shelter_pins)}件解決 / {len(skipped)}件スキップ")
        for src, cnt in sorted(src_counts.items()):
            print(f"  └ {src}: {cnt}件")
    else:
        print("[SKIP] shelter.csv なし（指定避難所PDFのOCR変換が必要）")

    aed_rows = read_csv("aed.csv")
    if aed_rows:
        aed_pins = parse_aed(aed_rows)
        all_pins.extend(aed_pins)
        print(f"AED: {len(aed_pins)}件")
    else:
        print("[WARN] aed.csv が見つかりません")

    manhole_rows = read_csv("manhole.csv")
    if manhole_rows:
        facility_pins = parse_manhole(manhole_rows, school_index, facility_index)
        toilet_count = sum(1 for p in facility_pins if p["category"] == "toilet")
        water_count  = sum(1 for p in facility_pins if p["category"] == "water")
        all_pins.extend(facility_pins)
        print(f"マンホールトイレ: {toilet_count}件、応急給水栓: {water_count}件")
    else:
        print("[SKIP] manhole.csv なし（手動整備が必要）")

    for p in all_pins:
        p.pop("_src", None)

    print(f"\n合計: {len(all_pins)}件")
    if all_skipped:
        print(f"スキップ（座標未解決）: {len(all_skipped)}件 → pins-data.json の \"skipped\" に記録")

    out = {
        "pins": all_pins,
        "skipped": all_skipped,
        "generatedAt": "2024-04-01",
        "source": "松山市オープンデータ (CC BY 4.0)",
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n出力完了: {OUT_PATH}")

    if all_skipped:
        print("\n── スキップ一覧（shelter_overrides.csv に手動追記してください）──")
        print("施設名,住所,lat,lng")
        for s in all_skipped:
            print(f"{s['name']},{s['address']},,")


if __name__ == "__main__":
    main()
