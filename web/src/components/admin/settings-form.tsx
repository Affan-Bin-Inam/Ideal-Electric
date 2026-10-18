"use client";

import { useState, type FormEvent } from "react";
import { refreshPublicSite } from "@/app/admin/actions";
import { CheckField, FormSection, TextArea, TextField } from "@/components/admin/fields";
import { adminFetch, describeError } from "@/lib/admin-api";
import type { AdminSiteSettings } from "@/lib/admin-types";

const ENDPOINT = "/api/v1/admin/site-settings";

// Every text field in the form. The checkbox is handled separately.
const TEXT_FIELDS = [
  "company_name",
  "tagline",
  "about_short",
  "phone_primary",
  "phone_secondary",
  "email_sales",
  "whatsapp_number",
  "address_line",
  "city",
  "google_maps_url",
  "business_hours",
  "facebook_url",
  "instagram_url",
  "linkedin_url",
  "default_meta_title",
  "default_meta_description",
] as const satisfies readonly (keyof AdminSiteSettings)[];

export function SettingsForm({ initial }: { initial: AdminSiteSettings }) {
  const [saved, setSaved] = useState(initial);
  const [version, setVersion] = useState(0); // changing it rebuilds the form with fresh values
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError(null);
    setErrors({});
    setNotice(null);

    // Send only what changed: untouched fields can't fail validation.
    const changes: Record<string, string | boolean | null> = {};
    for (const name of TEXT_FIELDS) {
      const next = String(data.get(name) ?? "").trim();
      const before = (saved[name] ?? "").trim();
      if (next !== before) changes[name] = next === "" ? null : next;
    }
    const placeholder = data.get("is_placeholder") === "on";
    if (placeholder !== saved.is_placeholder) changes.is_placeholder = placeholder;

    if (Object.keys(changes).length === 0) {
      setNotice("Nothing to save: no field was changed.");
      return;
    }

    setBusy(true);
    try {
      await adminFetch(ENDPOINT, { method: "PATCH", json: changes });
    } catch (err) {
      const described = describeError(err);
      setErrors(described.fields);
      setError(
        Object.keys(described.fields).length > 0
          ? "Please fix the highlighted fields."
          : described.general,
      );
      setBusy(false);
      return;
    }

    // Saved. Reload from the server so the form shows exactly what is stored.
    try {
      const fresh = await adminFetch<AdminSiteSettings>(ENDPOINT);
      setSaved(fresh);
      setVersion((v) => v + 1);
    } catch {
      // the save itself worked; the form just keeps what you typed
    }

    // Tell the public site to drop its cached copy of the settings.
    try {
      await refreshPublicSite(["site-settings"]);
      setNotice("Saved. The public site now shows the new details.");
    } catch {
      setNotice("Saved. The public site may take up to an hour to show the change.");
    }
    setBusy(false);
  }

  return (
    <form key={version} onSubmit={onSubmit} className="mt-6 space-y-6">
      <FormSection title="Company" description="Shown in the site footer and in search results.">
        <TextField
          name="company_name"
          label="Company name"
          required
          defaultValue={saved.company_name}
          error={errors.company_name}
        />
        <TextField
          name="tagline"
          label="Tagline"
          defaultValue={saved.tagline}
          error={errors.tagline}
        />
        <TextArea
          wide
          name="about_short"
          label="Short description"
          hint="A sentence or two, shown in the footer."
          defaultValue={saved.about_short}
          error={errors.about_short}
        />
      </FormSection>

      <FormSection
        title="Contact details"
        description="Any field you leave empty disappears from the public site."
      >
          <TextField
          name="phone_primary"
          label="Phone"
          type="tel"
          hint="Digits, with an optional + at the start. Spaces, hyphens and brackets are allowed."
          defaultValue={saved.phone_primary}
          error={errors.phone_primary}
        />
        <TextField
          name="phone_secondary"
          label="Second phone"
          type="tel"
          hint="Same format as the phone above."
          defaultValue={saved.phone_secondary}
          error={errors.phone_secondary}
        />
        <TextField
          name="email_sales"
          label="Sales email"
          type="email"
          defaultValue={saved.email_sales}
          error={errors.email_sales}
        />
        <TextField
          name="whatsapp_number"
          label="WhatsApp number"
          hint="International format, digits only, with no + and no spaces."
          defaultValue={saved.whatsapp_number}
          error={errors.whatsapp_number}
        />
        <TextField
          name="address_line"
          label="Address"
          defaultValue={saved.address_line}
          error={errors.address_line}
        />
        <TextField name="city" label="City" defaultValue={saved.city} error={errors.city} />
        <TextField
          wide
          name="google_maps_url"
          label="Google Maps link"
          type="url"
          hint="The full address, starting with https://"
          defaultValue={saved.google_maps_url}
          error={errors.google_maps_url}
        />
        <TextArea
          wide
          name="business_hours"
          label="Business hours"
          hint="Line breaks are kept on the website."
          defaultValue={saved.business_hours}
          error={errors.business_hours}
        />
      </FormSection>

      <FormSection title="Social media" description="Full addresses, starting with https://">
        <TextField
          name="facebook_url"
          label="Facebook"
          type="url"
          defaultValue={saved.facebook_url}
          error={errors.facebook_url}
        />
        <TextField
          name="instagram_url"
          label="Instagram"
          type="url"
          defaultValue={saved.instagram_url}
          error={errors.instagram_url}
        />
        <TextField
          name="linkedin_url"
          label="LinkedIn"
          type="url"
          defaultValue={saved.linkedin_url}
          error={errors.linkedin_url}
        />
      </FormSection>

      <FormSection
        title="Search engines"
        description="Used when a page has no title or description of its own."
      >
        <TextField
          wide
          name="default_meta_title"
          label="Default page title"
          hint="About 60 characters."
          defaultValue={saved.default_meta_title}
          error={errors.default_meta_title}
        />
        <TextArea
          wide
          name="default_meta_description"
          label="Default page description"
          hint="About 155 characters."
          defaultValue={saved.default_meta_description}
          error={errors.default_meta_description}
        />
      </FormSection>

      <FormSection title="Status">
        <CheckField
          name="is_placeholder"
          label="These details are still placeholders"
          hint="Untick this once the real details are entered."
          defaultChecked={saved.is_placeholder}
        />
      </FormSection>

      {error && (
        <p role="alert" className="rounded bg-white px-4 py-3 text-sm text-action shadow-sm">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="rounded bg-white px-4 py-3 text-sm shadow-sm">
          {notice}
        </p>
      )}

      <div className="flex items-center gap-4">
        <button
          disabled={busy}
          className="rounded bg-action px-6 py-3 font-semibold text-white hover:bg-action-hover disabled:opacity-60"
        >
          {busy ? "Saving…" : "Save changes"}
        </button>
        <p className="text-xs text-muted">
          Last saved {new Date(saved.updated_at).toLocaleString()}
        </p>
      </div>
    </form>
  );
}