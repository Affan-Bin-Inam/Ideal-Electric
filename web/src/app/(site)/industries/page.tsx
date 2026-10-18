import type { Metadata } from "next";
import Link from "next/link";
import { getIndustries } from "@/lib/industries";

export const metadata: Metadata = { title: "Industries" };

export default async function IndustriesPage() {
  const industries = await getIndustries();

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Industries</h1>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {industries.map((i) => (
          <Link
            key={i.id}
            href={`/industries/${i.slug}`}
            className="group rounded-lg border border-ink/10 bg-white p-5 hover:border-ink/30 hover:shadow-md"
          >
            <h2 className="font-semibold group-hover:text-action">{i.name}</h2>
            {i.summary && <p className="mt-1 text-sm text-muted">{i.summary}</p>}
          </Link>
        ))}
      </div>
    </div>
  );
}