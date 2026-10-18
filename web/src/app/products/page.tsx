import type { Metadata } from "next";
import { Suspense } from "react";
import { CatalogueResults, ResultsSkeleton } from "@/components/catalogue-results";
import type { SearchParams } from "@/lib/products";

export const metadata: Metadata = { title: "Products" };

export default function ProductsPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Products</h1>
      <Suspense fallback={<ResultsSkeleton />}>
        <CatalogueResults searchParams={searchParams} />
      </Suspense>
    </div>
  );
}