import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RepoMind AI",
  description: "Offline AI-powered GitHub repository intelligence platform"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

