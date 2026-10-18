import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ProductCard } from "@/components/product-card";
import { getIndustries } from "@/lib/industries";
import { catalogueHref, getProducts, toQuery, type CatalogueFilters } from "@/lib/products";

type Props = { params: Promise<{ slug: string }> };

export async function generateStaticParams() {
  const industries = await getIndustries();
  return industries.map((i) => ({ slug: i.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const industry = (await getIndustries()).find((i) => i.slug === slug);
  if (!industry) return {};
  return { title: industry.name, description: industry.summary ?? undefined };
}

// A thin wrapper: the slug is only known per request, so it is read inside <Suspense>.
export default function IndustryPage({ params }: Props) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
          <div className="h-64 animate-pulse rounded-lg bg-surface" />
        </div>
      }
    >
      {params.then(({ slug }) => (
        <IndustryContent slug={slug} />
      ))}
    </Suspense>
  );
}

async function IndustryContent({ slug }: { slug: string }) {
  const industry = (await getIndustries()).find((i) => i.slug === slug);
  if (!industry) notFound();

  // The same filters the catalogue uses, so "see all" lands on a matching page.
  const filters: CatalogueFilters = { attrs: [], page: 1, industry: slug };
  const data = await getProducts(toQuery(filters));

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link href="/industries" className="hover:text-action hover:underline">
          Industries
        </Link>
        <span aria-hidden> / </span>
        <span className="text-ink">{industry.name}</span>
      </nav>

      <h1 className="mt-4 text-3xl font-bold tracking-tight">{industry.name}</h1>
      {industry.summary && <p className="mt-2 max-w-2xl text-lg text-muted">{industry.summary}</p>}
      {industry.description && (
        <p className="mt-4 max-w-3xl whitespace-pre-line text-muted">{industry.description}</p>
      )}

      <h2 className="mt-12 text-xl font-bold tracking-tight">Products for {industry.name}</h2>

      {data.items.length === 0 ? (
        <div className="mt-6 rounded-lg bg-surface p-8 text-center">
          <p className="text-muted">No products are listed for this industry yet.</p>
          <Link
            href="/contact"
            className="mt-4 inline-block rounded bg-action px-5 py-3 font-semibold text-white hover:bg-action-hover"
          >
            Ask our sales team
          </Link>
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
          {data.total > data.items.length && (
            <p className="mt-8">
              <Link
                href={catalogueHref(filters)}
                className="font-semibold text-action hover:underline"
              >
                See all {data.total} products in the catalogue
              </Link>
            </p>
          )}
        </>
      )}
    </div>
  );
}