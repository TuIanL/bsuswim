import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智泳云枢 | AI Swim Motion Analysis",
  description:
    "智泳云枢是一套移动式双摄泳姿采集与AI姿态分析系统，面向竞技游泳训练、教练复盘和体育科研场景。"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
