import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AgentProof",
  description: "Independent outcome verification for AI agents.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b" style={{ borderColor: "var(--border)" }}>
          <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="font-semibold tracking-tight text-lg">AgentProof</span>
              <span className="text-xs text-muted hidden sm:inline" style={{ color: "var(--muted)" }}>
                Your agent says it&apos;s done. Check reality.
              </span>
            </Link>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t py-6" style={{ borderColor: "var(--border)" }}>
          <div className="mx-auto max-w-5xl px-6 text-xs" style={{ color: "var(--muted)" }}>
            Independent outcome verification for AI agents.
          </div>
        </footer>
      </body>
    </html>
  );
}
