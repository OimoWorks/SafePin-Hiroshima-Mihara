import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";

const GA_ID = "G-N02GWKB479";

export const metadata: Metadata = {
  title: "SafePin三原版",
  description: "三原市内の指定避難所・緊急避難場所・AED・公衆トイレをオフラインでも確認できる非公式の防災マップアプリ",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <meta name="theme-color" content="#E53E3E" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="SafePin三原版" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <meta property="og:title" content="SafePin三原版 - 三原市防災マップ（非公式）" />
        <meta property="og:description" content="三原市内の指定避難所・緊急避難場所・AED・公衆トイレをオフラインでも確認できる非公式の個人開発防災マップアプリ" />
        <meta property="og:type" content="website" />
        <meta property="og:image" content="https://safe-pin-hiroshima-mihara.vercel.app/ogp.png" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="SafePin三原版 - 三原市防災マップ（非公式）" />
        <meta name="twitter:description" content="三原市内の指定避難所・緊急避難場所・AED・公衆トイレをオフラインでも確認できる非公式の個人開発防災マップアプリ" />
        <meta name="twitter:image" content="https://safe-pin-hiroshima-mihara.vercel.app/ogp.png" />
      </head>
      <body className="antialiased">
        <Script
          src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
          strategy="afterInteractive"
        />
        <Script id="ga4-init" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '${GA_ID}');
          `}
        </Script>
        <ServiceWorkerRegister />
        {children}
      </body>
    </html>
  );
}
