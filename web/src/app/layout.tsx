import type { Metadata } from "next";
import "./globals.css";
import { getSiteSettings } from "@/lib/site-settings";
import { SITE_URL } from "@/lib/site-url";

export async function generateMetadata(): Promise<Metadata> {
  const s = await getSiteSettings();
  return {
    metadataBase: new URL(SITE_URL),
    title: {
      default: s.default_meta_title ?? s.company_name,
      template: `%s | ${s.company_name}`,
    },
    description: s.default_meta_description ?? undefined,
  };
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}