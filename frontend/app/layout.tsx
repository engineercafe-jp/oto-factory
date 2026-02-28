import type { Metadata } from "next";
import { Noto_Sans_JP, Zen_Kaku_Gothic_New } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";

const notoSans = Noto_Sans_JP({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

const zenKaku = Zen_Kaku_Gothic_New({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "oto-factory",
  description: "音楽生成ジョブを投入して進捗を監視するフロントエンド",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className={`${notoSans.variable} ${zenKaku.variable}`}>{children}</body>
    </html>
  );
}
