import { cacheLife, cacheTag } from "next/cache";
import { apiGet } from "@/lib/api";
import type { Category } from "@/lib/types";

export async function getCategories(): Promise<Category[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("categories");
  return apiGet<Category[]>("/api/v1/categories");
}

export function flattenCategories(nodes: Category[]): Category[] {
  return nodes.flatMap((c) => [c, ...flattenCategories(c.children)]);
}