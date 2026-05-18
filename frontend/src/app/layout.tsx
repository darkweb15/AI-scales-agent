import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SalesAI — Automation Dashboard",
  description: "Multi-agent AI sales automation platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
