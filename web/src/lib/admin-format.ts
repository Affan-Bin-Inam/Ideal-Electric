// The server sends times without a timezone marker; they are treated as UTC
// and shown in the viewer's own timezone.
export function formatDateTime(iso: string): string {
  const hasZone = /([zZ]|[+-]\d{2}:\d{2})$/.test(iso);
  const date = new Date(hasZone ? iso : `${iso}Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}