import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SalesAI — Agentic Sales Platform",
  description: "Pure AI-driven sales automation with autonomous agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg-base text-text-primary antialiased">{children}</body>
    </html>
  );
}
