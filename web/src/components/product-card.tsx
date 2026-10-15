import Link from "next/link";
import type { ProductCardData } from "@/lib/types";

export function ProductCard({ product }: { product: ProductCardData }) {
  return (
    <Link
      href={`/products/${product.slug}`}
      className="group flex flex-col overflow-hidden rounded-lg border border-ink/10 bg-white transition hover:border-ink/30 hover:shadow-md"
    >
      <div className="flex aspect-[4/3] items-center justify-center bg-surface text-xs font-semibold uppercase tracking-wider text-muted">
        Image coming soon
      </div>
      <div className="flex flex-1 flex-col p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">
          {product.series.name} · {product.category.name}
        </p>
        <h3 className="mt-1 font-semibold group-hover:text-action">{product.name}</h3>
        {product.model_code && (
          <p className="mt-0.5 text-xs text-muted">Model {product.model_code}</p>
        )}
        {product.summary && <p className="mt-2 text-sm text-muted">{product.summary}</p>}
      </div>
    </Link>
  );
}