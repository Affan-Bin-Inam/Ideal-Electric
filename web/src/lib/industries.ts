import { cacheLife, cacheTag } from "next/cache";
import { apiGet } from "@/lib/api";
import type { Industry } from "@/lib/types";

export async function getIndustries(): Promise<Industry[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("industries");
  return apiGet<Industry[]>("/api/v1/industries");
}