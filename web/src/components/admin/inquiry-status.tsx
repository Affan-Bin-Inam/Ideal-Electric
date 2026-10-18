const STYLES: Record<string, string> = {
  new: "bg-brand-yellow text-ink",
  contacted: "bg-ink/10 text-ink",
  quoted: "bg-brand-green text-ink",
  closed: "bg-surface text-muted ring-1 ring-ink/10",
  spam: "bg-action/10 text-action",
};

export const statusLabel = (status: string) => status.charAt(0).toUpperCase() + status.slice(1);

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        STYLES[status] ?? "bg-surface text-muted"
      }`}
    >
      {statusLabel(status)}
    </span>
  );
}