import { SITE_URL } from "@/lib/site-url";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ProductCard } from "@/components/product-card";
import { telHref, whatsappHref } from "@/lib/contact";
import { getAllProductSlugs, getProduct } from "@/lib/product-detail";
import { catalogueHref } from "@/lib/products";
import { getSiteSettings } from "@/lib/site-settings";
import type { Specification } from "@/lib/types";
import { InquiryForm } from "@/components/inquiry-form";
import { Suspense } from "react";

type Props = { params: Promise<{ slug: string }> };

export async function generateStaticParams() {
  const slugs = await getAllProductSlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) return {};
  return {
    title: product.seo_title ?? product.name,
    description: product.seo_description ?? product.summary ?? undefined,
    alternates: { canonical: `/products/${product.slug}` },
  };
}

function formatSpec(spec: Specification): string {
  const value = Array.isArray(spec.value) ? spec.value.join(", ") : spec.value;
  return spec.unit ? `${value} ${spec.unit}` : value;
}

const primary =
  "inline-block rounded bg-action px-5 py-3 font-semibold text-white hover:bg-action-hover";
const secondary =
  "inline-block rounded border border-ink/30 px-5 py-3 font-semibold hover:border-ink";

// export default async function ProductPage({ params }: Props) {
//   const { slug } = await params;
export default function ProductPage({ params }: Props) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <div className="h-96 animate-pulse rounded-lg bg-surface" />
        </div>
      }
    >
      {params.then(({ slug }) => (
        <ProductContent slug={slug} />
      ))}
    </Suspense>
  );
}

async function ProductContent({ slug }: { slug: string }) {
  const [product, settings] = await Promise.all([getProduct(slug), getSiteSettings()]);
  if (!product) notFound();

  // Contact buttons appear only for details that really exist.
  const message = `Hello ${settings.company_name}, I'd like a quote for ${product.name}${
    product.model_code ? ` (model ${product.model_code})` : ""
  }.`;
  const whatsapp = whatsappHref(settings.whatsapp_number, message);
  const email = settings.email_sales
    ? `mailto:${settings.email_sales}?subject=${encodeURIComponent(
        `Quote request: ${product.name}`,
      )}&body=${encodeURIComponent(message)}`
    : null;
  const call = telHref(settings.phone_primary);

  // Specs the visitor chooses from when asking for a quote (here: which ratings).
  const inquiryOptions = product.specifications
    .filter((s) => s.is_inquiry_option && Array.isArray(s.value) && s.value.length > 1)
    .map((s) => ({ key: s.key, label: s.label, unit: s.unit, values: s.value as string[] }));

  const crumbs = [
    { label: "Products", href: "/products" },
    ...(product.parent_category
      ? [
          {
            label: product.parent_category.name,
            href: catalogueHref({ attrs: [], page: 1, category: product.parent_category.slug }),
          },
        ]
      : []),
    {
      label: product.category.name,
      href: catalogueHref({ attrs: [], page: 1, category: product.category.slug }),
    },
  ];

  const specGroups = new Map<string, Specification[]>();
  for (const spec of product.specifications) {
    const group = spec.group_name ?? "Specifications";
    specGroups.set(group, [...(specGroups.get(group) ?? []), spec]);
  }
  // Structured data: tells search engines what this page is. There's no price or stock
  // because you don't publish them, so there is deliberately no "offers" block.
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Product",
        name: product.name,
        description: product.description ?? product.summary ?? undefined,
        ...(product.model_code ? { model: product.model_code, mpn: product.model_code } : {}),
        ...(product.brand ? { brand: { "@type": "Brand", name: product.brand.name } } : {}),
        category: product.category.name,
        url: `${SITE_URL}/products/${product.slug}`,
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [...crumbs, { label: product.name, href: `/products/${product.slug}` }].map(
          (c, i) => ({
            "@type": "ListItem",
            position: i + 1,
            name: c.label,
            item: `${SITE_URL}${c.href}`,
          }),
        ),
      },
    ],
  };
  const heading = "text-xl font-bold tracking-tight";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
      />
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
          {crumbs.map((c) => (
            <li key={c.href} className="flex items-center gap-2">
              <Link href={c.href} className="hover:text-action hover:underline">
                {c.label}
              </Link>
              <span aria-hidden>/</span>
            </li>
          ))}
          <li aria-current="page" className="text-ink">
            {product.name}
          </li>
        </ol>
      </nav>

      <div className="mt-6 grid gap-10 lg:grid-cols-2">
        <div className="flex aspect-[4/3] items-center justify-center rounded-lg bg-surface text-xs font-semibold uppercase tracking-wider text-muted">
          Image coming soon
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">
            {[product.series?.name, product.brand?.name].filter(Boolean).join(" · ")}
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">{product.name}</h1>
          {product.model_code && (
            <p className="mt-1 text-sm text-muted">Model {product.model_code}</p>
          )}
          {product.summary && <p className="mt-4 text-lg text-muted">{product.summary}</p>}

          <div className="mt-6 flex flex-wrap gap-3">
            {whatsapp && (
              <a href={whatsapp} target="_blank" rel="noopener noreferrer" className={primary}>
                Quote on WhatsApp
              </a>
            )}
            <a href="#inquiry" className={whatsapp ? secondary : primary}>
              Send an inquiry
            </a>
            {email && (
              <a href={email} className={secondary}>
                Email us
              </a>
            )}
            {call && (
              <a href={call} className={secondary}>
                Call sales
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="mt-12 max-w-3xl space-y-10">
        {product.features.length > 0 && (
          <section>
            <h2 className={heading}>Key features</h2>
            <ul className="mt-3 list-disc space-y-1 pl-5">
              {product.features.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </section>
        )}

        {product.description && (
          <section>
            <h2 className={heading}>Description</h2>
            <p className="mt-3 whitespace-pre-line text-muted">{product.description}</p>
          </section>
        )}

        {specGroups.size > 0 && (
          <section>
            <h2 className={heading}>Specifications</h2>
            {[...specGroups].map(([group, specs]) => (
              <div key={group} className="mt-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                  {group}
                </h3>
                <dl className="mt-2 divide-y divide-ink/10 rounded-lg border border-ink/10">
                  {specs.map((spec) => (
                    <div key={spec.key} className="grid grid-cols-3 gap-4 px-4 py-3 text-sm">
                      <dt className="text-muted">{spec.label}</dt>
                      <dd className="col-span-2 font-medium">{formatSpec(spec)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </section>
        )}
      </div>

        <section id="inquiry" className="mt-16 max-w-3xl scroll-mt-24">
        <h2 className={heading}>Request a quote</h2>
        <p className="mt-2 text-muted">
          Tell us what you need for {product.name} and we will get back to you.
        </p>
        <div className="mt-6">
          <InquiryForm productSlug={product.slug} options={inquiryOptions} />
        </div>
      </section>

      {product.related.length > 0 && (
        <section className="mt-16">
          <h2 className={heading}>Related products</h2>
          <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {product.related.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}