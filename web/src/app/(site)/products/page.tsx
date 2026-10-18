import type { Metadata } from "next";
import { Suspense } from "react";
import { CatalogueResults, ResultsSkeleton } from "@/components/catalogue-results";
import { flattenCategories, getCategories } from "@/lib/categories";
import { parseFilters, type SearchParams } from "@/lib/products";

type Props = { searchParams: SearchParams };

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const f = parseFilters(await searchParams);
  const onlyCategory =
    f.category && !f.series && !f.industry && !f.q && f.attrs.length === 0 && !f.sort && f.page === 1;
  const nothing =
    !f.category && !f.series && !f.industry && !f.q && f.attrs.length === 0 && !f.sort && f.page === 1;

  if (nothing) {
    return { title: "Products", alternates: { canonical: "/products" } };
  }

  // A single category is a real landing page: its own title, indexable, canonical to itself.
  if (onlyCategory) {
    const category = flattenCategories(await getCategories()).find((c) => c.slug === f.category);
    if (category) {
      return {
        title: category.name,
        description: category.description ?? undefined,
        alternates: { canonical: `/products?category=${encodeURIComponent(category.slug)}` },
      };
    }
  }

  // Every other combination: don't index it, but follow its links.
  return {
    title: "Products",
    robots: { index: false, follow: true },
    alternates: { canonical: "/products" },
  };
}

export default function ProductsPage({ searchParams }: Props) {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Products</h1>
      <Suspense fallback={<ResultsSkeleton />}>
        <CatalogueResults searchParams={searchParams} />
      </Suspense>
    </div>
  );
}