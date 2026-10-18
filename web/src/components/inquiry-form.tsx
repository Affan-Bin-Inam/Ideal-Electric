"use client";

import Script from "next/script";
import { useEffect, useRef, useState, type FormEvent } from "react";

export type InquiryOption = {
  key: string;
  label: string;
  unit: string | null;
  values: string[];
};

type Props = { productSlug?: string; options?: InquiryOption[] };

declare global {
  interface Window {
    turnstile?: {
      render: (
        el: HTMLElement,
        opts: {
          sitekey: string;
          callback?: (token: string) => void;
          "expired-callback"?: () => void;
          "error-callback"?: () => void;
        },
      ) => string;
      remove: (id: string) => void;
    };
  }
}

const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

// Draws the Cloudflare check. It lives in its own component so it is removed
// together with the form, and a new `key` gives a fresh widget (tokens work once).
function TurnstileBox({ onToken }: { onToken: (token: string) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!ready || !SITE_KEY || !box.current || !window.turnstile) return;
    const id = window.turnstile.render(box.current, {
      sitekey: SITE_KEY,
      callback: onToken,
      "expired-callback": () => onToken(""),
      "error-callback": () => onToken(""),
    });
    return () => window.turnstile?.remove(id);
  }, [ready, onToken]);

  if (!SITE_KEY) {
    return process.env.NODE_ENV === "development" ? (
      <p className="text-sm text-action">
        Missing NEXT_PUBLIC_TURNSTILE_SITE_KEY in web/.env.local (restart the dev server after adding it).
      </p>
    ) : null;
  }

  return (
    <>
      <Script
        src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
        strategy="afterInteractive"
        onReady={() => setReady(true)}
      />
      <div ref={box} />
    </>
  );
}

// Reads FastAPI's standard validation errors: {"detail": [{"loc": ["body", "email"], "msg": "..."}]}
function readErrors(status: number, body: unknown) {
  const fields: Record<string, string> = {};
  let general: string | null = null;
  const detail = (body as { detail?: unknown } | null)?.detail;

  if (Array.isArray(detail)) {
    for (const item of detail) {
      const loc = (item as { loc?: unknown[] }).loc;
      const msg = (item as { msg?: unknown }).msg;
      const field = Array.isArray(loc) ? loc[loc.length - 1] : undefined;
      if (typeof field === "string" && typeof msg === "string") fields[field] = msg;
    }
  } else if (typeof detail === "string") {
    general = detail;
  }

  if (Object.keys(fields).length === 0 && !general) {
    general =
      status === 429
        ? "Too many requests. Please wait a little and try again."
        : "Something went wrong. Please try again, or contact us directly.";
  }
  return { fields, general };
}

const inputClass = "mt-1 w-full rounded border border-ink/20 px-3 py-2 text-sm";

function Field(props: {
  name: string;
  label: string;
  type?: string;
  required?: boolean;
  autoComplete?: string;
  error?: string;
}) {
  return (
    <div>
      <label htmlFor={props.name} className="text-sm font-semibold">
        {props.label}
        {props.required && <span aria-hidden> *</span>}
      </label>
      <input
        id={props.name}
        name={props.name}
        type={props.type ?? "text"}
        required={props.required}
        autoComplete={props.autoComplete}
        aria-invalid={props.error ? true : undefined}
        className={inputClass}
      />
      {props.error && <p className="mt-1 text-sm text-action">{props.error}</p>}
    </div>
  );
}

export function InquiryForm({ productSlug, options = [] }: Props) {
  const [status, setStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [token, setToken] = useState("");
  const [attempt, setAttempt] = useState(0);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const text = (name: string) => String(data.get(name) ?? "").trim();

    setError(null);
    setFieldErrors({});

    // My rule, not the backend's: a form with no way to reach the visitor is useless.
    if (!text("phone") && !text("email")) {
      setFieldErrors({ phone: "Please give a phone number or an email so we can reply." });
      return;
    }
    if (!token) {
      setError("Please complete the spam check first.");
      return;
    }

    const selected: Record<string, string[]> = {};
    for (const option of options) {
      const values = data.getAll(`option:${option.key}`).map(String);
      if (values.length > 0) selected[option.key] = values;
    }

    const payload = {
      name: text("name"),
      phone: text("phone") || undefined,
      email: text("email") || undefined,
      company: text("company") || undefined,
      city: text("city") || undefined,
      message: text("message") || undefined,
      product_slug: productSlug,
      selected_options: Object.keys(selected).length > 0 ? selected : undefined,
      source_page: window.location.pathname,
      turnstile_token: token,
      website: text("website"), // honeypot: stays empty for real visitors
    };

    setStatus("sending");
    try {
      const res = await fetch("/api/v1/inquiries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setStatus("sent");
        return;
      }
      const { fields, general } = readErrors(res.status, await res.json().catch(() => null));
      setFieldErrors(fields);
      setError(general);
      setStatus("idle");
    } catch {
      setError("We couldn't reach the server. Please try again, or contact us directly.");
      setStatus("idle");
    } finally {
      setToken("");
      setAttempt((a) => a + 1); // a fresh Turnstile widget for the next try
    }
  }

  if (status === "sent") {
    return (
      <div role="status" className="rounded-lg border border-brand-green bg-brand-green/15 p-6 text-ink">
        <p className="font-semibold">Thank you, your inquiry has been sent.</p>
        <p className="mt-1 text-sm">We will get back to you using the details you gave.</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field name="name" label="Your name" required autoComplete="name" error={fieldErrors.name} />
        <Field name="phone" label="Phone" type="tel" autoComplete="tel" error={fieldErrors.phone} />
        <Field name="email" label="Email" type="email" autoComplete="email" error={fieldErrors.email} />
        <Field name="company" label="Company" autoComplete="organization" error={fieldErrors.company} />
        <Field name="city" label="City" error={fieldErrors.city} />
      </div>

      {options.map((option) => (
        <fieldset key={option.key}>
          <legend className="text-sm font-semibold">
            {option.label}
            {option.unit ? ` (${option.unit})` : ""} you need
          </legend>
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
            {option.values.map((value) => (
              <label key={value} className="flex items-center gap-2 text-sm">
                <input type="checkbox" name={`option:${option.key}`} value={value} />
                {value}
              </label>
            ))}
          </div>
        </fieldset>
      ))}

      <div>
        <label htmlFor="message" className="text-sm font-semibold">
          Message
        </label>
        <textarea
          id="message"
          name="message"
          rows={4}
          aria-invalid={fieldErrors.message ? true : undefined}
          className={inputClass}
        />
        {fieldErrors.message && <p className="mt-1 text-sm text-action">{fieldErrors.message}</p>}
      </div>

      {/* Honeypot: invisible to people, tempting to bots. */}
      <div aria-hidden className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
        <label>
          Website
          <input name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>

      <TurnstileBox key={attempt} onToken={setToken} />

      {error && (
        <p role="alert" className="rounded bg-surface px-4 py-3 text-sm text-action">
          {error}
        </p>
      )}

      <button
        disabled={status === "sending"}
        className="rounded bg-action px-6 py-3 font-semibold text-white hover:bg-action-hover disabled:opacity-60"
      >
        {status === "sending" ? "Sending…" : "Send inquiry"}
      </button>
    </form>
  );
}