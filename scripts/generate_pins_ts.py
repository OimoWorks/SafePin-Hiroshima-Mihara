#!/usr/bin/env python3
"""
lib/pins-data.json から lib/pins.ts を再生成するスクリプト
build_pins.py で pins-data.json を生成した後に実行する

Usage: python3 scripts/generate_pins_ts.py
"""

import json
import os
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, "..", "lib")
JSON_PATH = os.path.join(LIB_DIR, "pins-data.json")
TS_PATH = os.path.join(LIB_DIR, "pins.ts")


def main():
    if not os.path.exists(JSON_PATH):
        print(f"[ERROR] {JSON_PATH} が見つかりません。先に build_pins.py を実行してください。")
        return

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    pins = data["pins"]
    generated_at = data.get("generatedAt", "")
    source = data.get("source", "松山市オープンデータ (CC BY 4.0)")

    def detail_str(p: dict) -> str:
        cat = p["category"]
        d = p["detail"]
        if cat in ("shelter", "evacuation_site", "toilet"):
            cap = d.get("capacity", 0)
            notes = d.get("notes", "")
            return f'{{ capacity: {cap}, notes: {json.dumps(notes, ensure_ascii=False)} }}'
        elif cat == "water":
            amt = d.get("supplyAmount", "")
            notes = d.get("notes", "")
            return f'{{ supplyAmount: {json.dumps(amt, ensure_ascii=False)}, notes: {json.dumps(notes, ensure_ascii=False)} }}'
        elif cat == "aed":
            facility = d.get("facilityName", "")
            notes = d.get("notes", "")
            return f'{{ facilityName: {json.dumps(facility, ensure_ascii=False)}, notes: {json.dumps(notes, ensure_ascii=False)} }}'
        return '{}'

    lines = [
        "import { Pin } from './types'",
        "",
        f"// 出典: {source}",
        f"// 生成日: {generated_at}",
        "// このファイルは scripts/generate_pins_ts.py で自動生成されます。直接編集しないでください。",
        "",
        "export const DUMMY_PINS: Pin[] = [",
    ]

    for p in pins:
        lines.append("  {")
        lines.append(f"    id: {json.dumps(p['id'])},")
        lines.append(f"    category: '{p['category']}',")
        lines.append(f"    name: {json.dumps(p['name'], ensure_ascii=False)},")
        lines.append(f"    address: {json.dumps(p['address'], ensure_ascii=False)},")
        lines.append(f"    lat: {p['lat']},")
        lines.append(f"    lng: {p['lng']},")
        lines.append(f"    detail: {detail_str(p)},")
        lines.append(f"    updatedAt: {json.dumps(p['updatedAt'])},")
        lines.append("  } as Pin,")

    lines.append("]")
    lines.append("")

    content = "\n".join(lines)
    with open(TS_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"生成完了: {TS_PATH} ({len(pins)}件)")
    cats = Counter(p["category"] for p in pins)
    for cat, cnt in sorted(cats.items()):
        print(f"  {cat}: {cnt}件")


if __name__ == "__main__":
    main()
