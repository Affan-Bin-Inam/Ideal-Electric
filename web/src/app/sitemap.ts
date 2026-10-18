// src/app/sitemap.ts
import type { MetadataRoute } from "next";
import { getIndustries } from "@/lib/industries";
import { getProductSlugs } from "@/lib/product-detail";
import { SITE_URL } from "@/lib/site-url";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [slugs, industries] = await Promise.all([getProductSlugs(), getIndustries()]);
  const url = (path: string) => `${SITE_URL}${path}`;

  return [
    { url: url("/") },
    { url: url("/products") },
    { url: url("/industries") },
    { url: url("/contact") },
    ...industries.map((i) => ({ url: url(`/industries/${i.slug}`) })),
    ...slugs.map((slug) => ({ url: url(`/products/${slug}`) })),
  ];
}