import { cacheLife, cacheTag } from "next/cache";
import { apiGet } from "@/lib/api";
import type { HomepageResponse } from "@/lib/types";

export async function getHomepage(): Promise<HomepageResponse> {
  "use cache";
  cacheLife("minutes");
  cacheTag("homepage");
  return apiGet<HomepageResponse>("/api/v1/homepage");
}