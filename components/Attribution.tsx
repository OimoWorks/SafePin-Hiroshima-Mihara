export default function Attribution() {
  return (
    <div className="absolute bottom-0 left-0 z-[1000] bg-white/80 text-gray-500 text-[10px] leading-tight px-2 py-1 rounded-tr-lg max-w-[240px]">
      本アプリは
      <a
        href="https://hiroshima-opendata.dataeye.jp/"
        target="_blank"
        rel="noopener noreferrer"
        className="underline"
      >
        三原市オープンデータ
      </a>
      ・
      <a
        href="https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html"
        target="_blank"
        rel="noopener noreferrer"
        className="underline"
      >
        国土地理院指定緊急避難場所データ
      </a>
      （指定避難所・AED・公衆トイレ 等）を加工して作成（CC BY 4.0）。非公式の個人開発アプリです。
    </div>
  )
}
