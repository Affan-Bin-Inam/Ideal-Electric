"use client";

import { useSession } from "@/components/admin/admin-shell";

export default function Dashboard() {
  const { user } = useSession();
  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
      <p className="mt-2 text-muted">
        Signed in as {user.email}
        {user.role ? ` (${user.role})` : ""}.
      </p>
      <p className="mt-6 text-sm text-muted">
        The editing screens will appear in the menu as we build them.
      </p>
    </div>
  );
}