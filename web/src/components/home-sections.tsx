import Link from "next/link";
import { ProductCard } from "@/components/product-card";
import type { HomepageSection } from "@/lib/types";

type Props = { section: HomepageSection };

function Cta({ section, variant = "solid" }: Props & { variant?: "solid" | "link" }) {
  if (!section.cta_label || !section.cta_url) return null;
  const style =
    variant === "solid"
      ? "inline-block rounded bg-action px-6 py-3 font-semibold text-white hover:bg-action-hover"
      : "font-semibold text-action hover:underline";
  return (
    <Link href={section.cta_url} className={style}>
      {section.cta_label}
    </Link>
  );
}

function Heading({ section }: Props) {
  return (
    <div className="mb-8 max-w-2xl">
      <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">{section.heading}</h2>
      {section.subheading && <p className="mt-2 text-muted">{section.subheading}</p>}
    </div>
  );
}

function Hero({ section }: Props) {
  return (
    <section className="bg-surface">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24">
        <div aria-hidden className="mb-6 flex h-1.5 w-24">
          <span className="flex-1 bg-brand-green" />
          <span className="flex-1 bg-brand-yellow" />
          <span className="flex-1 bg-brand-red" />
        </div>
        <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          {section.heading}
        </h1>
        {section.subheading && (
          <p className="mt-4 max-w-2xl text-lg text-muted">{section.subheading}</p>
        )}
        <div className="mt-8">
          <Cta section={section} />
        </div>
      </div>
    </section>
  );
}

function FeaturedProducts({ section }: Props) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
      <Heading section={section} />
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {section.products.map((p) => (
          <ProductCard key={p.id} product={p} />
        ))}
      </div>
      <div className="mt-8">
        <Cta section={section} variant="link" />
      </div>
    </section>
  );
}

function Industries({ section }: Props) {
  return (
    <section className="bg-surface">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <Heading section={section} />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {section.industries.map((i) => (
            <Link
              key={i.id}
              href={`/industries/${i.slug}`}
              className="group rounded-lg border border-ink/10 bg-white p-5 hover:border-ink/30 hover:shadow-md"
            >
              <h3 className="font-semibold group-hover:text-action">{i.name}</h3>
              {i.summary && <p className="mt-1 text-sm text-muted">{i.summary}</p>}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

const ACCENTS = ["border-brand-green", "border-brand-yellow", "border-brand-red"];

function WhyChooseUs({ section }: Props) {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
      <Heading section={section} />
      <div className="grid gap-8 md:grid-cols-3">
        {section.items.map((item, index) => (
          <div key={item.title} className={`border-t-4 pt-4 ${ACCENTS[index % ACCENTS.length]}`}>
            <h3 className="font-semibold">{item.title}</h3>
            <p className="mt-2 text-sm text-muted">{item.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function InquiryCta({ section }: Props) {
  return (
    <section className="bg-ink text-white">
      <div className="mx-auto max-w-7xl px-4 py-14 text-center sm:px-6">
        <h2 className="text-2xl font-bold sm:text-3xl">{section.heading}</h2>
        {section.subheading && (
          <p className="mx-auto mt-2 max-w-xl text-white/70">{section.subheading}</p>
        )}
        <div className="mt-6">
          <Cta section={section} />
        </div>
      </div>
    </section>
  );
}

export function SectionRenderer({ section }: Props) {
  switch (section.key) {
    case "hero":
      return <Hero section={section} />;
    case "featured_products":
      return <FeaturedProducts section={section} />;
    case "industries":
      return <Industries section={section} />;
    case "why_choose_us":
      return <WhyChooseUs section={section} />;
    case "inquiry_cta":
      return <InquiryCta section={section} />;
    default:
      return null; // a section key we don't know yet: ignore it
  }
}