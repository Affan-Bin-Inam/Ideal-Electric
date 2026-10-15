import Image from "next/image";

const swatches = [
  ["bg-ink text-white", "ink"],
  ["bg-action text-white", "action"],
  ["bg-brand-yellow text-ink", "yellow"],
  ["bg-brand-green text-ink", "green"],
  ["bg-surface text-ink", "surface"],
] as const;

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <Image src="/ideal-logo.svg" alt="Ideal Electric" width={296} height={115} priority />
      <p className="mt-6 text-muted">Muted secondary text on white.</p>
      <div className="mt-6 flex flex-wrap gap-3">
        {swatches.map(([classes, name]) => (
          <div key={name} className={`${classes} rounded px-4 py-6 text-sm font-semibold`}>
            {name}
          </div>
        ))}
      </div>
      <button className="mt-6 rounded bg-action px-5 py-3 font-semibold text-white hover:bg-action-hover">
        Inquire on WhatsApp
      </button>
    </main>
  );
}