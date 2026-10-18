"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { useSession } from "@/components/admin/admin-shell";
import { StatusBadge, statusLabel } from "@/components/admin/inquiry-status";
import { AdminApiError, adminFetch, describeError } from "@/lib/admin-api";
import { formatDateTime } from "@/lib/admin-format";
import { INQUIRY_STATUSES, type InquiryDetailData } from "@/lib/admin-types";
import { telHref } from "@/lib/contact";

const card = "rounded-lg bg-white p-6 shadow-sm";
const smallButton =
  "rounded border border-ink/20 px-3 py-1.5 text-sm font-semibold hover:border-ink disabled:opacity-60";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 py-2 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="col-span-2 break-words">{children}</dd>
    </div>
  );
}

const prettyKey = (key: string) => {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

export function InquiryDetail({ id }: { id: number }) {
  const { user } = useSession();
  const url = `/api/v1/admin/inquiries/${id}`;

  const [state, setState] = useState<{
    id: number;
    detail?: InquiryDetailData;
    problem?: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");

  useEffect(() => {
    let cancelled = false;
    adminFetch<InquiryDetailData>(url)
      .then((detail) => {
        if (!cancelled) setState({ id, detail });
      })
      .catch((err) => {
        if (cancelled) return;
        const missing = err instanceof AdminApiError && err.status === 404;
        setState({
          id,
          problem: missing
            ? "This inquiry doesn't exist."
            : (describeError(err).general ?? "Couldn't load the inquiry."),
        });
      });
    return () => {
      cancelled = true;
    };
  }, [id, url]);

  const current = state?.id === id ? state : null;
  const detail = current?.detail;

  // Run a change, then reload the inquiry so the screen shows exactly what is stored.
  async function change(run: () => Promise<unknown>, done: string): Promise<boolean> {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await run();
      setState({ id, detail: await adminFetch<InquiryDetailData>(url) });
      setNotice(done);
      return true;
    } catch (err) {
      const described = describeError(err);
      setError(described.general ?? Object.values(described.fields).join(" "));
      return false;
    } finally {
      setBusy(false);
    }
  }

  function save(patch: { status?: string; assigned_to_id?: number | null }) {
    if (!detail) return;
    void change(
      () =>
        adminFetch(url, {
          method: "PATCH",
          json: { status: detail.status, assigned_to_id: detail.assigned_to_id, ...patch },
        }),
      "Saved.",
    );
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    const body = noteText.trim();
    if (!body) return;
    const ok = await change(
      () => adminFetch(`${url}/notes`, { method: "POST", json: { body } }),
      "Note added.",
    );
    if (ok) setNoteText("");
  }

  if (!current) return <p className="text-muted">Loading…</p>;
  if (!detail) {
    return (
      <div>
        <p role="alert" className="text-action">
          {current.problem}
        </p>
        <Link href="/admin/inquiries" className="mt-4 inline-block text-sm font-semibold text-action">
          ← All inquiries
        </Link>
      </div>
    );
  }

  const phone = telHref(detail.phone);
  const options = detail.selected_options ? Object.entries(detail.selected_options) : [];

  return (
    <div>
      <Link href="/admin/inquiries" className="text-sm font-semibold text-action hover:underline">
        ← All inquiries
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold tracking-tight">{detail.name}</h1>
        <StatusBadge status={detail.status} />
      </div>
      <p className="mt-1 text-sm text-muted">Received {formatDateTime(detail.created_at)}</p>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          <section className={card}>
            <h2 className="font-bold">Contact</h2>
            <dl className="mt-2 divide-y divide-ink/10">
              <Row label="Phone">
                {detail.phone ? (
                  phone ? (
                    <a href={phone} className="text-action hover:underline">
                      {detail.phone}
                    </a>
                  ) : (
                    detail.phone
                  )
                ) : (
                  "—"
                )}
              </Row>
              <Row label="WhatsApp">
                {detail.whatsapp_url ? (
                  <a
                    href={detail.whatsapp_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-action hover:underline"
                  >
                    Open chat
                  </a>
                ) : (
                  "—"
                )}
              </Row>
              <Row label="Email">
                {detail.email ? (
                  <a href={`mailto:${detail.email}`} className="text-action hover:underline">
                    {detail.email}
                  </a>
                ) : (
                  "—"
                )}
              </Row>
              <Row label="Company">{detail.company ?? "—"}</Row>
              <Row label="City">{detail.city ?? "—"}</Row>
            </dl>
          </section>

          <section className={card}>
            <h2 className="font-bold">Request</h2>
            <dl className="mt-2 divide-y divide-ink/10">
              <Row label="Product">{detail.product_name ?? "General inquiry"}</Row>
              {options.map(([key, values]) => (
                <Row key={key} label={prettyKey(key)}>
                  {values.join(", ")}
                </Row>
              ))}
              <Row label="Sent from">{detail.source_page ?? "—"}</Row>
            </dl>
            <p className="mt-4 whitespace-pre-line text-sm">
              {detail.message ?? <span className="text-muted">No message.</span>}
            </p>
          </section>
        </div>

        <div className="space-y-6">
          <section className={card}>
            <h2 className="font-bold">Handling</h2>

            <label htmlFor="status" className="mt-4 block text-sm font-semibold">
              Status
            </label>
            <select
              id="status"
              value={detail.status}
              disabled={busy}
              onChange={(e) => save({ status: e.target.value })}
              className="mt-1 w-full rounded border border-ink/20 bg-white px-3 py-2 text-sm"
            >
              {INQUIRY_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {statusLabel(s)}
                </option>
              ))}
            </select>

            <p className="mt-4 text-sm font-semibold">Assigned to</p>
            <p className="mt-1 text-sm">{detail.assigned_to_email ?? "Nobody yet"}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {detail.assigned_to_id !== user.id && (
                <button
                  disabled={busy}
                  onClick={() => save({ assigned_to_id: user.id })}
                  className={smallButton}
                >
                  Assign to me
                </button>
              )}
              {detail.assigned_to_id !== null && (
                <button
                  disabled={busy}
                  onClick={() => save({ assigned_to_id: null })}
                  className={smallButton}
                >
                  Unassign
                </button>
              )}
            </div>

            {error && (
              <p role="alert" className="mt-4 text-sm text-action">
                {error}
              </p>
            )}
            {notice && (
              <p role="status" className="mt-4 text-sm">
                {notice}
              </p>
            )}
          </section>

          <section className={card}>
            <h2 className="font-bold">Notes</h2>
            {detail.notes.length === 0 ? (
              <p className="mt-3 text-sm text-muted">No notes yet.</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {detail.notes.map((note) => (
                  <li key={note.id} className="rounded bg-surface p-3 text-sm">
                    <p className="whitespace-pre-line">{note.body}</p>
                    <p className="mt-1 text-xs text-muted">
                      {[note.author_email, formatDateTime(note.created_at)]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </li>
                ))}
              </ul>
            )}
            <form onSubmit={addNote} className="mt-4">
              <label htmlFor="note" className="text-sm font-semibold">
                Add a note
              </label>
              <textarea
                id="note"
                rows={3}
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                className="mt-1 w-full rounded border border-ink/20 bg-white px-3 py-2 text-sm"
              />
              <button
                disabled={busy || noteText.trim() === ""}
                className="mt-2 rounded bg-action px-4 py-2 text-sm font-semibold text-white hover:bg-action-hover disabled:opacity-60"
              >
                Add note
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}