# SafePin データ整備スクリプト

## 実行順序

```
scripts/
├── fetch_data.py          # Step 1: CSVダウンロード
├── scrape_manhole.py      # Step 2: マンホールHTML→CSV
├── parse_shelter_pdf.py   # Step 3: 指定避難所PDF→CSV（手動補完が必要な場合あり）
├── build_pins.py          # Step 4: 全データ統合 → lib/pins-data.json
├── generate_pins_ts.py    # Step 5: JSON → lib/pins.ts 自動生成
└── raw/                   # 中間ファイル置き場（gitignore対象）
```

## Step 1: CSVダウンロード

```bash
python3 scripts/fetch_data.py
```

`scripts/raw/` に以下が生成されます：
- `evacuation.csv` — 緊急避難場所（座標あり）
- `aed.csv` — AED設置箇所（座標あり）
- `school.csv` — 学校施設座標（他データの座標補完に使用）

## Step 2: マンホールトイレ・給水栓スクレイプ

```bash
python3 scripts/scrape_manhole.py
```

`scripts/raw/manhole.csv` が生成されます。
列: `学校名, 応急給水栓, マンホールトイレ基数, 整備年度`

ページ構造が変わっている場合は手動で作成してください。

## Step 3: 指定避難所PDF変換

```bash
python3 scripts/parse_shelter_pdf.py "/mnt/user-data/uploads/松山市指定避難所.pdf"
```

PDFがベクター描画の場合、テキスト抽出に失敗します。
その場合は `scripts/raw/shelter.csv` を手動で作成してください。

**shelter.csv フォーマット:**
```
NO,地区名,施設名,住所,地震,津波,高潮,洪水,土砂
1,中央地区,松山市役所,愛媛県松山市二番町四丁目7-2,○,×,×,×,×
```

対応可否: `○`（対応）、`△`（条件付き）、`×`（非対応）

## Step 4: データ統合

```bash
python3 scripts/build_pins.py
```

`lib/pins-data.json` が生成されます。

## Step 5: TypeScript生成

```bash
python3 scripts/generate_pins_ts.py
```

`lib/pins.ts` が実データで上書きされます。その後 `npm run build` で確認。

---

## ライセンス

本スクリプトで取得するデータのライセンス:

> 本アプリは以下のデータを加工して作成しています。  
> 指定緊急避難場所一覧、AED設置箇所一覧、学校施設の施設名・位置情報  
> **松山市**、クリエイティブ・コモンズ・ライセンス 表示4.0（CC BY 4.0）
