import { cacheLife, cacheTag } from "next/cache";
import { apiGet } from "@/lib/api";
import type { SiteSettings } from "@/lib/types";

export async function getSiteSettings(): Promise<SiteSettings> {
  "use cache";
  cacheLife("hours"); // reuse the result for a while
  cacheTag("site-settings"); // a label, so we can invalidate it later
  return apiGet<SiteSettings>("/api/v1/site-settings");
}