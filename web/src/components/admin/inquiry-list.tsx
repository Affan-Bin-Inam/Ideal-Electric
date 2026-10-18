"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { StatusBadge, statusLabel } from "@/components/admin/inquiry-status";
import { adminFetch, describeError } from "@/lib/admin-api";
import { formatDateTime } from "@/lib/admin-format";
import { INQUIRY_STATUSES, type InquiryListData } from "@/lib/admin-types";

const PAGE_SIZE = 25;

function hrefFor(f: { status?: string; q?: string; page?: number }) {
  const p = new URLSearchParams();
  if (f.status) p.set("status", f.status);
  if (f.q) p.set("q", f.q);
  if (f.page && f.page > 1) p.set("page", String(f.page));
  const query = p.toString();
  return query ? `/admin/inquiries?${query}` : "/admin/inquiries";
}

const th = "px-4 py-3 font-semibold";

export function InquiryList() {
  const router = useRouter();
  const params = useSearchParams();
  const status = params.get("status") ?? "";
  const q = params.get("q") ?? "";
  const page = Math.max(1, Number.parseInt(params.get("page") ?? "1", 10) || 1);

  const apiQuery = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (status) apiQuery.set("status", status);
  if (q) apiQuery.set("q", q);
  const key = apiQuery.toString();

  // The result remembers which request it answers, so a stale answer is never shown.
  const [result, setResult] = useState<{
    key: string;
    data?: InquiryListData;
    problem?: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    adminFetch<InquiryListData>(`/api/v1/admin/inquiries?${key}`)
      .then((data) => {
        if (!cancelled) setResult({ key, data });
      })
      .catch((error) => {
        if (!cancelled) {
          setResult({
            key,
            problem: describeError(error).general ?? "Couldn't load the inquiries.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [key]);

  const current = result?.key === key ? result : null;

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = String(new FormData(event.currentTarget).get("q") ?? "").trim();
    router.push(hrefFor({ status, q: value }));
  }

  const tabs = [
    { value: "", label: "All" },
    ...INQUIRY_STATUSES.map((s) => ({ value: s as string, label: statusLabel(s) })),
  ];

  return (
    <div>
      <nav aria-label="Filter by status" className="mt-4 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Link
            key={t.value}
            href={hrefFor({ status: t.value, q })}
            aria-current={status === t.value ? "true" : undefined}
            className={`rounded-full px-3 py-1 text-sm ${
              status === t.value ? "bg-ink text-white" : "bg-white hover:bg-ink/10"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </nav>

      <form key={q} onSubmit={onSearch} role="search" className="mt-4 flex max-w-md gap-2">
        <input
          type="search"
          name="q"
          defaultValue={q}
          maxLength={100}
          placeholder="Search name, phone, company…"
          aria-label="Search inquiries"
          className="min-w-0 flex-1 rounded border border-ink/20 bg-white px-3 py-2 text-sm"
        />
        <button className="rounded bg-action px-4 py-2 text-sm font-semibold text-white hover:bg-action-hover">
          Search
        </button>
      </form>

      {!current && <p className="mt-6 text-muted">Loading…</p>}
      {current?.problem && (
        <p role="alert" className="mt-6 text-action">
          {current.problem}
        </p>
      )}

      {current?.data && (
        <>
          <p className="mt-4 text-sm text-muted">
            {current.data.total} {current.data.total === 1 ? "inquiry" : "inquiries"}
          </p>

          {current.data.items.length === 0 ? (
            <p className="mt-4 rounded-lg bg-white p-8 text-center text-muted shadow-sm">
              No inquiries match.
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto rounded-lg bg-white shadow-sm">
              <table className="w-full min-w-[44rem] text-left text-sm">
                <thead className="border-b border-ink/10 text-xs uppercase tracking-wider text-muted">
                  <tr>
                    <th className={th}>Received</th>
                    <th className={th}>Name</th>
                    <th className={th}>Phone</th>
                    <th className={th}>Product</th>
                    <th className={th}>Status</th>
                    <th className={th}>Assigned to</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/10">
                  {current.data.items.map((i) => (
                    <tr key={i.id} className="hover:bg-surface">
                      <td className="whitespace-nowrap px-4 py-3 text-muted">
                        {formatDateTime(i.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/admin/inquiries/${i.id}`}
                          className="font-semibold text-action hover:underline"
                        >
                          {i.name}
                        </Link>
                        {i.company && <span className="block text-xs text-muted">{i.company}</span>}
                      </td>
                      <td className="px-4 py-3">{i.phone ?? "—"}</td>
                      <td className="px-4 py-3">{i.product_name ?? "General inquiry"}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={i.status} />
                      </td>
                      <td className="px-4 py-3 text-muted">{i.assigned_to_email ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {current.data.pages > 1 && (
            <nav aria-label="Pagination" className="mt-6 flex items-center justify-between">
              {page > 1 ? (
                <Link
                  href={hrefFor({ status, q, page: page - 1 })}
                  className="rounded border border-ink/20 bg-white px-4 py-2 text-sm font-semibold"
                >
                  Previous
                </Link>
              ) : (
                <span />
              )}
              <span className="text-sm text-muted">
                Page {page} of {current.data.pages}
              </span>
              {page < current.data.pages ? (
                <Link
                  href={hrefFor({ status, q, page: page + 1 })}
                  className="rounded border border-ink/20 bg-white px-4 py-2 text-sm font-semibold"
                >
                  Next
                </Link>
              ) : (
                <span />
              )}
            </nav>
          )}
        </>
      )}
    </div>
  );
}