import { Suspense } from "react";
import { InquiryList } from "@/components/admin/inquiry-list";

export default function InquiriesPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Inquiries</h1>
      <Suspense fallback={<p className="mt-6 text-muted">Loading…</p>}>
        <InquiryList />
      </Suspense>
    </div>
  );
}