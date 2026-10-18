"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession } from "@/components/admin/admin-shell";
import { adminFetch } from "@/lib/admin-api";
import type { InquiryListData } from "@/lib/admin-types";

export default function Dashboard() {
  const { user } = useSession();
  const [newCount, setNewCount] = useState<number | null>(null);

  useEffect(() => {
    // page_size=1: we only want the total, not the inquiries themselves
    adminFetch<InquiryListData>("/api/v1/admin/inquiries?status=new&page=1&page_size=1")
      .then((data) => setNewCount(data.total))
      .catch(() => setNewCount(null));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
      <p className="mt-2 text-muted">Welcome, {user.full_name}.</p>

      <Link
        href="/admin/inquiries?status=new"
        className="mt-6 block max-w-xs rounded-lg bg-white p-6 shadow-sm hover:shadow-md"
      >
        <p className="text-sm text-muted">New inquiries</p>
        <p className="mt-1 text-3xl font-bold">{newCount ?? "—"}</p>
      </Link>
    </div>
  );
}