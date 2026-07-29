import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import { Inter } from "next/font/google";
import { Providers } from "@/components/Providers";
import { RoleProvider } from "@/components/dashboard/RoleProvider";
import { ServiceWorkerRegister } from "@/components/ServiceWorkerRegister";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "BMW AI Automotive Intelligence Platform",
  description: "Real-time driver monitoring, ADAS, and fleet management",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "BMW Driver",
  },
  icons: {
    icon: [{ url: "/icons/icon-192.svg", type: "image/svg+xml" }],
    apple: [{ url: "/icons/icon-192.svg" }],
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const roleCookie = cookies().get("bmw_role")?.value ?? null;

  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body className={`${inter.className} bg-[var(--bg)] text-[var(--fg)]`}>
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <Providers>
          <RoleProvider role={roleCookie}>{children}</RoleProvider>
        </Providers>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
