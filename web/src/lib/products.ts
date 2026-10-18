import { cacheLife, cacheTag } from "next/cache";
import { apiGet } from "@/lib/api";
import type { Facets, ProductList } from "@/lib/types";

type RawParams = Record<string, string | string[] | undefined>;
export type SearchParams = Promise<RawParams>;

export const SORT_OPTIONS = [
  { value: "featured", label: "Featured" },
  { value: "name", label: "Name" },
  { value: "newest", label: "Newest" },
] as const;
const SORT_VALUES: string[] = ["relevance", "featured", "name", "newest"];

export type CatalogueFilters = {
  category?: string;
  series?: string;
  industry?: string;
  q?: string;
  sort?: string;
  attrs: string[]; // each one "key:value", for example "poles:2"
  page: number;
};

// The attribute format lives here and nowhere else.
export const attrToken = (key: string, value: string) => `${key}:${value}`;
export function parseAttrToken(token: string) {
  const i = token.indexOf(":");
  return { key: token.slice(0, i), value: token.slice(i + 1) };
}

function list(value: string | string[] | undefined): string[] {
  const arr = Array.isArray(value) ? value : value === undefined ? [] : [value];
  return arr.map((v) => v.trim()).filter(Boolean);
}

// URL text in, clean filters out. Anything the API would reject is dropped here.
export function parseFilters(raw: RawParams): CatalogueFilters {
  const q = list(raw.q)[0];
  const validQ = q && q.length >= 2 ? q.slice(0, 100) : undefined;
  const sort = list(raw.sort)[0];
  const page = Number.parseInt(list(raw.page)[0] ?? "1", 10);
  const attrs = [...new Set(list(raw.attr))]
    .filter((a) => a.length <= 80 && /^[a-z0-9_-]+:.+$/i.test(a))
    .slice(0, 20);

  return {
    category: list(raw.category)[0],
    series: list(raw.series)[0],
    industry: list(raw.industry)[0],
    q: validQ,
    sort:
      sort && SORT_VALUES.includes(sort) && (sort !== "relevance" || validQ)
        ? sort
        : undefined,
    attrs,
    page: Number.isFinite(page) && page >= 1 ? page : 1,
  };
}

function buildQuery(f: CatalogueFilters, withPaging: boolean): string {
  const p = new URLSearchParams();
  if (f.category) p.set("category", f.category);
  if (f.series) p.set("series", f.series);
  if (f.industry) p.set("industry", f.industry);
  if (f.q) p.set("q", f.q);
  for (const a of [...f.attrs].sort()) p.append("attr", a); // sorted: same filters, same cache key
  if (withPaging) {
    if (f.sort) p.set("sort", f.sort);
    if (f.page > 1) p.set("page", String(f.page));
  }
  return p.toString();
}

export const toQuery = (f: CatalogueFilters) => buildQuery(f, true); // for the product list
export const toFacetQuery = (f: CatalogueFilters) => buildQuery(f, false); // facets take no sort or page

export function catalogueHref(f: CatalogueFilters): string {
  const query = toQuery(f);
  return query ? `/products?${query}` : "/products";
}

// Change a filter; any change sends the visitor back to page 1.
export function withPatch(
  f: CatalogueFilters,
  patch: Partial<CatalogueFilters>,
): CatalogueFilters {
  return { ...f, ...patch, page: 1 };
}

export function toggleAttr(
  f: CatalogueFilters,
  attr: { key: string; data_type: string },
  value: string,
): CatalogueFilters {
  const token = attrToken(attr.key, value);
  let attrs: string[];
  if (f.attrs.includes(token)) {
    attrs = f.attrs.filter((a) => a !== token);
  } else if (attr.data_type === "single_choice") {
    // one value per attribute: replace the old choice
    attrs = [...f.attrs.filter((a) => parseAttrToken(a).key !== attr.key), token];
  } else {
    attrs = [...f.attrs, token];
  }
  return { ...f, attrs, page: 1 };
}

export async function getProducts(query: string): Promise<ProductList> {
  "use cache";
  cacheLife("minutes");
  cacheTag("products");
  return apiGet<ProductList>(`/api/v1/products${query ? `?${query}` : ""}`);
}

export async function getFacets(query: string): Promise<Facets> {
  "use cache";
  cacheLife("minutes");
  cacheTag("products");
  return apiGet<Facets>(`/api/v1/products/facets${query ? `?${query}` : ""}`);
}