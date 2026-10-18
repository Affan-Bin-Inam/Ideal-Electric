"use client";

import { useEffect, useState } from "react";
import { SettingsForm } from "@/components/admin/settings-form";
import { adminFetch, describeError } from "@/lib/admin-api";
import type { AdminSiteSettings } from "@/lib/admin-types";

export default function SettingsPage() {
  const [settings, setSettings] = useState<AdminSiteSettings | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    adminFetch<AdminSiteSettings>("/api/v1/admin/site-settings")
      .then(setSettings)
      .catch((error) => setProblem(describeError(error).general));
  }, []);

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold tracking-tight">Site settings</h1>
      <p className="mt-1 text-sm text-muted">
        Contact details and texts used across the public website.
      </p>
      {problem && (
        <p role="alert" className="mt-6 text-action">
          {problem}
        </p>
      )}
      {!settings && !problem && <p className="mt-6 text-muted">Loading…</p>}
      {settings && <SettingsForm initial={settings} />}
    </div>
  );
}