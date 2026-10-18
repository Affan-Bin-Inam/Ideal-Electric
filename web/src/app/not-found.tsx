import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-24 text-center sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Page not found</h1>
      <p className="mt-2 text-muted">This page doesn't exist or has moved.</p>
      <Link
        href="/products"
        className="mt-6 inline-block rounded bg-action px-5 py-3 font-semibold text-white hover:bg-action-hover"
      >
        Browse products
      </Link>
    </div>
  );
}