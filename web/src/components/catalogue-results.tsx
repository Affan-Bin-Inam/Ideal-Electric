import Link from "next/link";
import { ProductCard } from "@/components/product-card";
import { ActiveFilters, FilterPanel, SortLinks } from "@/components/catalogue-filters";
import { getCategories } from "@/lib/categories";
import { getIndustries } from "@/lib/industries";
import {
  catalogueHref,
  getFacets,
  getProducts,
  parseFilters,
  toFacetQuery,
  toQuery,
  type CatalogueFilters,
  type SearchParams,
} from "@/lib/products";

export async function CatalogueResults({ searchParams }: { searchParams: SearchParams }) {
  const filters = parseFilters(await searchParams);

  // Three independent requests: start them together instead of one after another.
  const [data, facets, categories, industries] = await Promise.all([
    getProducts(toQuery(filters)),
    getFacets(toFacetQuery(filters)),
    getCategories(),
    getIndustries()
  ]);
  console.log("sidebar data:", { categories: categories.length, series: facets.series.length });

    const panel = <FilterPanel filters={filters} facets={facets} categories={categories} />;
    const filtered = Boolean(
    filters.category || filters.series || filters.industry || filters.q || filters.attrs.length,
    );

  return (
    <div className="mt-6 lg:grid lg:grid-cols-[16rem_1fr] lg:gap-10">
      {/* Wide screens: a sidebar. */}
      <aside className="hidden lg:block">{panel}</aside>

      <div>
        {/* Phones: the same panel inside a native disclosure, with no JavaScript. */}
        <details className="mb-6 rounded-lg border border-ink/10 lg:hidden">
          <summary className="cursor-pointer px-4 py-3 text-sm font-semibold">Filters</summary>
          <div className="border-t border-ink/10 p-4">{panel}</div>
        </details>

        {/* A plain GET form. It keeps the other filters and returns to page 1. */}
        <form action="/products" method="get" role="search" className="flex max-w-xl gap-2">
          {filters.category && <input type="hidden" name="category" value={filters.category} />}
          {filters.series && <input type="hidden" name="series" value={filters.series} />}
          {filters.industry && <input type="hidden" name="industry" value={filters.industry} />}
          {filters.sort && <input type="hidden" name="sort" value={filters.sort} />}
          {filters.attrs.map((a) => (
            <input key={a} type="hidden" name="attr" value={a} />
          ))}
          <input
            type="search"
            name="q"
            defaultValue={filters.q ?? ""}
            minLength={2}
            maxLength={100}
            placeholder="Search products"
            aria-label="Search products"
            className="min-w-0 flex-1 rounded border border-ink/20 px-3 py-2 text-sm"
          />
          <button className="rounded bg-action px-4 py-2 text-sm font-semibold text-white hover:bg-action-hover">
            Search
          </button>
        </form>

        <ActiveFilters filters={filters} facets={facets} categories={categories} industries={industries} />

        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted">
            {data.total} {data.total === 1 ? "product" : "products"}
            {filtered && (
              <>
                {" · "}
                <Link href="/products" className="font-semibold text-action hover:underline">
                  Clear all
                </Link>
              </>
            )}
          </p>
          <SortLinks filters={filters} />
        </div>

        {data.items.length === 0 ? (
          <p className="mt-8 rounded-lg bg-surface p-8 text-center text-muted">
            No products match these filters.
          </p>
        ) : (
          <div className="mt-6 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {data.items.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )}

        <Pagination filters={filters} pages={data.pages} />
      </div>
    </div>
  );
}

function Pagination({ filters, pages }: { filters: CatalogueFilters; pages: number }) {
  if (pages <= 1) return null;
  const current = Math.min(filters.page, pages);
  const button =
    "rounded border border-ink/20 px-4 py-2 text-sm font-semibold hover:border-ink/50";

  return (
    <nav aria-label="Pagination" className="mt-10 flex items-center justify-between">
      {current > 1 ? (
        <Link href={catalogueHref({ ...filters, page: current - 1 })} className={button}>
          Previous
        </Link>
      ) : (
        <span />
      )}
      <span className="text-sm text-muted">
        Page {current} of {pages}
      </span>
      {current < pages ? (
        <Link href={catalogueHref({ ...filters, page: current + 1 })} className={button}>
          Next
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}

export function ResultsSkeleton() {
  return (
    <div aria-hidden className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="h-72 animate-pulse rounded-lg bg-surface" />
      ))}
    </div>
  );
}