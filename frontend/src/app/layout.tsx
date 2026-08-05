import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";
import { ThemeProvider } from "./theme-provider";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { AuthNav } from "@/features/auth/components/AuthNav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Dev Framework",
  description: "AI Dev Framework 프론트엔드",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <Providers>
            <header className="border-b border-border">
              <nav className="mx-auto flex max-w-5xl items-center justify-between gap-6 px-6 py-4">
                <div className="flex items-center gap-6">
                  <Link href="/" className="font-semibold">
                    AI Dev Framework
                  </Link>
                  <Link href="/agent-tasks" className="text-sm text-muted-foreground hover:text-foreground">
                    에이전트 작업
                  </Link>
                </div>
                <div className="flex items-center gap-4">
                  <AuthNav />
                  <ThemeToggle />
                </div>
              </nav>
            </header>
            <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">{children}</main>
            <footer className="border-t border-border">
              <div className="mx-auto max-w-5xl px-6 py-4 text-sm text-muted-foreground">
                AI Dev Framework
              </div>
            </footer>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
