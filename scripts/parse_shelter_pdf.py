#!/usr/bin/env python3
"""
指定避難所PDF → shelter.csv 変換スクリプト
Usage: python3 scripts/parse_shelter_pdf.py <PDFパス>
       例: python3 scripts/parse_shelter_pdf.py "/mnt/user-data/uploads/松山市指定避難所.pdf"
出力: scripts/raw/shelter.csv

注意: このPDFはベクター描画のテーブルのため pdfplumber のテキスト抽出が
      うまくいかない可能性があります。その場合は shelter.csv を手動で作成してください。

shelter.csv のフォーマット:
  NO,地区名,施設名,住所,地震,津波,高潮,洪水,土砂
  1,中央地区,松山市役所,愛媛県松山市二番町四丁目7-2,○,×,×,×,×
"""

import csv
import os
import re
import sys

try:
    import pdfplumber
except ImportError:
    print("pdfplumber が必要です: pip install pdfplumber")
    sys.exit(1)

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(RAW_DIR, exist_ok=True)
OUT = os.path.join(RAW_DIR, "shelter.csv")

FIELDNAMES = ["NO", "地区名", "施設名", "住所", "地震", "津波", "高潮", "洪水", "土砂"]


def clean(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"ファイルが見つかりません: {pdf_path}")
        sys.exit(1)

    print(f"読み込み: {pdf_path}")
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        print(f"ページ数: {len(pdf.pages)}")
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"  Page {page_num}...", end=" ", flush=True)
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        cleaned = [clean(cell) for cell in row]
                        if cleaned[0] in ("NO", "No", "番号", "") or not any(cleaned):
                            continue
                        rows.append(cleaned)
                print(f"テーブル {len(tables)}個, {sum(len(t) for t in tables)}行")
            else:
                text = page.extract_text() or ""
                line_count = len([l for l in text.split("\n") if l.strip()])
                print(f"テキストのみ ({line_count}行) ※テーブル未検出")

    if not rows:
        print("\n[警告] テーブルデータが抽出できませんでした。")
        print("このPDFはベクター描画形式の可能性があります。")
        print("手動でshelter.csvを作成するか、Adobe Acrobat等でテキスト変換してください。")
        print(f"\n期待するフォーマット: {', '.join(FIELDNAMES)}")
        with open(OUT, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerow({
                "NO": "1", "地区名": "（手動入力してください）",
                "施設名": "", "住所": "",
                "地震": "○", "津波": "×", "高潮": "×", "洪水": "×", "土砂": "×",
            })
        print(f"\nサンプルCSV出力: {OUT}")
        sys.exit(1)

    print(f"\n合計 {len(rows)}行 抽出")
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDNAMES)
        for row in rows:
            while len(row) < len(FIELDNAMES):
                row.append("")
            writer.writerow(row[:len(FIELDNAMES)])

    print(f"出力: {OUT}")
    print("※ 内容を確認し、列がずれている場合は手動で修正してください。")


if __name__ == "__main__":
    main()
