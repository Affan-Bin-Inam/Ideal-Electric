import Link from "next/link";
import {
  SORT_OPTIONS,
  attrToken,
  catalogueHref,
  parseAttrToken,
  toggleAttr,
  withPatch,
  type CatalogueFilters,
} from "@/lib/products";
import type { Category, Facets, Industry } from "@/lib/types";

type Props = { filters: CatalogueFilters; facets: Facets; categories: Category[]; industries?: Industry[] };

const heading = "text-xs font-semibold uppercase tracking-wider text-muted";

function Item(props: { href: string; active: boolean; label: string; count?: number }) {
  return (
    <Link
      href={props.href}
      aria-current={props.active ? "true" : undefined}
      className={`flex items-baseline justify-between gap-2 rounded px-2 py-1 text-sm hover:bg-surface ${
        props.active ? "font-semibold text-action" : ""
      }`}
    >
      <span>{props.label}</span>
      {props.count !== undefined && <span className="text-xs text-muted">{props.count}</span>}
    </Link>
  );
}

// Is this category the selected one, or does it contain the selected one?
function isOpen(node: Category, slug?: string): boolean {
  return !!slug && (node.slug === slug || node.children.some((c) => isOpen(c, slug)));
}

function flatten(nodes: Category[]): Category[] {
  return nodes.flatMap((c) => [c, ...flatten(c.children)]);
}

// A tree that calls itself for the next level down. Children show only inside the open branch.
function CategoryTree(props: {
  nodes: Category[];
  selected?: string;
  hrefFor: (slug: string) => string;
  nested?: boolean;
}) {
  const visible = props.nodes.filter((c) => c.product_count > 0);
  if (visible.length === 0) return null;
  return (
    <ul className={props.nested ? "ml-2 border-l border-ink/10 pl-1" : "mt-2 space-y-0.5"}>
      {visible.map((c) => (
        <li key={c.id}>
          <Item
            href={props.hrefFor(c.slug)}
            active={props.selected === c.slug}
            label={c.name}
            count={c.product_count}
          />
          {isOpen(c, props.selected) && (
            <CategoryTree
              nodes={c.children}
              selected={props.selected}
              hrefFor={props.hrefFor}
              nested
            />
          )}
        </li>
      ))}
    </ul>
  );
}

export function FilterPanel({ filters, facets, categories }: Props) {
  // Clicking the active option again removes the filter.
  const categoryHref = (slug: string) =>
    catalogueHref(withPatch(filters, { category: filters.category === slug ? undefined : slug }));
  const seriesHref = (slug: string) =>
    catalogueHref(withPatch(filters, { series: filters.series === slug ? undefined : slug }));

  return (
    <div className="space-y-6">
      {categories.length > 0 && (
        <section>
          <h2 className={heading}>Categories</h2>
          <CategoryTree nodes={categories} selected={filters.category} hrefFor={categoryHref} />
        </section>
      )}

      {facets.series.length > 0 && (
        <section>
          <h2 className={heading}>Series</h2>
          <ul className="mt-2 space-y-0.5">
            {facets.series.map((s) => (
              <li key={s.slug}>
                <Item
                  href={seriesHref(s.slug)}
                  active={filters.series === s.slug}
                  label={s.name}
                  count={s.count}
                />
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Attributes such as "Poles" only make sense inside one product family. */}
      {filters.category &&
        facets.attributes.map((attr) => (
          <section key={attr.key}>
            <h2 className={heading}>
              {attr.label}
              {attr.unit ? ` (${attr.unit})` : ""}
            </h2>
            <ul className="mt-2 space-y-0.5">
              {attr.options.map((o) => (
                <li key={o.value}>
                  <Item
                    href={catalogueHref(toggleAttr(filters, attr, o.value))}
                    active={filters.attrs.includes(attrToken(attr.key, o.value))}
                    label={o.value}
                    count={o.count}
                  />
                </li>
              ))}
            </ul>
          </section>
        ))}
    </div>
  );
}

export function ActiveFilters({ filters, facets, categories, industries = [] }: Props) {
  const chips: { label: string; href: string }[] = [];

  if (filters.category) {
    const name =
      flatten(categories).find((c) => c.slug === filters.category)?.name ?? filters.category;
    chips.push({ label: name, href: catalogueHref(withPatch(filters, { category: undefined })) });
  }
  if (filters.series) {
    const name = facets.series.find((s) => s.slug === filters.series)?.name ?? filters.series;
    chips.push({ label: name, href: catalogueHref(withPatch(filters, { series: undefined })) });
  }
  if (filters.industry) {
    chips.push({
      label: industries.find((i) => i.slug === filters.industry)?.name ?? filters.industry.replace(/-/g, " "),
      href: catalogueHref(withPatch(filters, { industry: undefined })),
    });
  }
  if (filters.q) {
    chips.push({
      label: `“${filters.q}”`,
      href: catalogueHref(withPatch(filters, { q: undefined })),
    });
  }
  for (const token of filters.attrs) {
    const { key, value } = parseAttrToken(token);
    const attr = facets.attributes.find((a) => a.key === key);
    chips.push({
      label: attr ? `${attr.label}: ${value}${attr.unit ? ` ${attr.unit}` : ""}` : token,
      href: catalogueHref({ ...filters, attrs: filters.attrs.filter((a) => a !== token), page: 1 }),
    });
  }

  if (chips.length === 0) return null;
  return (
    <ul className="mt-4 flex flex-wrap gap-2">
      {chips.map((c) => (
        <li key={c.href}>
          <Link
            href={c.href}
            aria-label={`Remove filter: ${c.label}`}
            className="inline-flex items-center gap-1.5 rounded-full bg-surface px-3 py-1 text-sm hover:bg-ink/10"
          >
            {c.label}
            <span aria-hidden>×</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function SortLinks({ filters }: { filters: CatalogueFilters }) {
  const options: { value: string; label: string }[] = [
    ...(filters.q ? [{ value: "relevance", label: "Relevance" }] : []),
    ...SORT_OPTIONS,
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
      <span className="text-muted">Sort by</span>
      {options.map((o) => {
        const active = filters.sort === o.value;
        return (
          <Link
            key={o.value}
            href={catalogueHref(withPatch(filters, { sort: active ? undefined : o.value }))}
            aria-current={active ? "true" : undefined}
            className={active ? "font-semibold text-action" : "hover:underline"}
          >
            {o.label}
          </Link>
        );
      })}
    </div>
  );
}