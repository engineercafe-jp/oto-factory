import type { Metadata } from "next";
import { Noto_Sans_JP, Zen_Kaku_Gothic_New, Geist } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

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
  description: "テキストプロンプトから音楽を生成するAIコンポーザー",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="ja" className={cn("font-sans", geist.variable)}>
      <body className={`${notoSans.variable} ${zenKaku.variable}`}>{children}</body>
    </html>
  );
}
