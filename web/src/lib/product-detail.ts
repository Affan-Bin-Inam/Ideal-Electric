import { cacheLife, cacheTag } from "next/cache";
import { ApiError, apiGet } from "@/lib/api";
import type { ProductDetail, ProductList } from "@/lib/types";

// Returns null for an unknown slug, so the page can show a proper 404.
export async function getProduct(slug: string): Promise<ProductDetail | null> {
  "use cache";
  cacheLife("minutes");
  cacheTag("products", `product:${slug}`);
  try {
    return await apiGet<ProductDetail>(`/api/v1/products/${encodeURIComponent(slug)}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error; // anything else is a real problem: let it show
  }
}

// Used at build time to list every product page. The API allows 48 per page at most.
export async function getAllProductSlugs(): Promise<string[]> {
  const slugs: string[] = [];
  let page = 1;
  let pages = 1;
  do {
    const data = await apiGet<ProductList>(`/api/v1/products?page=${page}&page_size=48`);
    slugs.push(...data.items.map((p) => p.slug));
    pages = data.pages;
    page += 1;
  } while (page <= pages);
  return slugs;
}

// A cached copy for the sitemap, so it doesn't call the API on every request.
export async function getProductSlugs(): Promise<string[]> {
  "use cache";
  cacheLife("hours");
  cacheTag("products");
  return getAllProductSlugs();
}