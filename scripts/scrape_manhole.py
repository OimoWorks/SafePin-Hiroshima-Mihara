#!/usr/bin/env python3
"""
松山市 応急給水栓・マンホールトイレ一覧ページをスクレープして manhole.csv を生成
Usage: python3 scripts/scrape_manhole.py
"""

import csv
import os
import re
import sys
import requests
from html.parser import HTMLParser

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(RAW_DIR, exist_ok=True)
OUT = os.path.join(RAW_DIR, "manhole.csv")

URL = "https://www.city.matsuyama.ehime.jp/kurashi/kurashi/josuido/tetuzuki/saigaisonae/oukyukyusuimanhole.html"


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_td = False
        self.current_row = []
        self.current_cell = ""
        self.rows = []
        self.headers = []
        self.header_done = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        if tag in ("td", "th") and self.in_table:
            self.in_td = True
            self.current_cell = ""
        if tag == "tr" and self.in_table:
            self.current_row = []

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        if tag in ("td", "th") and self.in_table:
            self.current_row.append(self.current_cell.strip())
            self.in_td = False
        if tag == "tr" and self.in_table and self.current_row:
            if not self.header_done:
                self.headers = self.current_row
                self.header_done = True
            else:
                self.rows.append(self.current_row)

    def handle_data(self, data):
        if self.in_td:
            self.current_cell += data


def main():
    print(f"Fetching: {URL}")
    try:
        r = requests.get(URL, timeout=20, headers={"User-Agent": "SafePin/1.0"})
        r.raise_for_status()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

    enc = r.apparent_encoding or "utf-8"
    html = r.content.decode(enc, errors="replace")

    parser = TableParser()
    parser.feed(html)

    if not parser.rows:
        print("テーブルが見つかりませんでした。HTMLを手動で確認してください。")
        sys.exit(1)

    print(f"ヘッダー: {parser.headers}")
    print(f"行数: {len(parser.rows)}")

    # セル結合された見出し行（エリア名・地区名）を除外するパターン
    _AREA_PATTERN = re.compile(r'エリア|地区|地域|中心部')

    fieldnames = ["学校名", "応急給水栓", "マンホールトイレ基数", "整備年度"]
    written = 0
    skipped = 0

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in parser.rows:
            while len(row) < 4:
                row.append("")
            # 1列目（施設名）を取得し、PDF注記を除去
            raw_name = re.sub(r'[（(]PDF[^）)]*[）)]', '', row[0]).strip()
            # エリア見出し行・空行・地区名のみの行はスキップ
            if not raw_name or _AREA_PATTERN.search(raw_name):
                skipped += 1
                continue
            row[0] = raw_name
            writer.writerow(row[:4])
            written += 1

    print(f"\n出力: {OUT}（{written}件、{skipped}行スキップ）")
    print("※ 列の順序が正しいか確認し、必要なら手動で修正してください。")


if __name__ == "__main__":
    main()
