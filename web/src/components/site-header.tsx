import Image from "next/image";
import Link from "next/link";
import { getSiteSettings } from "@/lib/site-settings";

const NAV = [
  { href: "/products", label: "Products" },
  { href: "/industries", label: "Industries" },
];

export async function SiteHeader() {
  const s = await getSiteSettings();

  return (
    <header className="sticky top-0 z-40 border-b border-ink/10 bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-8 gap-y-1 px-4 py-2 sm:px-6">
        <Link href="/" aria-label={`${s.company_name} home`}>
          <Image
            src="/ideal-logo.svg"
            alt={s.company_name}
            width={296}
            height={115}
            priority
            className="h-11 w-auto"
          />
        </Link>

        <nav
          aria-label="Main"
          className="order-last flex w-full items-center gap-6 text-sm font-semibold sm:order-none sm:w-auto sm:flex-1 sm:gap-8"
        >
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className="py-2 hover:text-action">
              {item.label}
            </Link>
          ))}
        </nav>

        <Link
          href="/contact"
          className="rounded bg-action px-4 py-2 text-sm font-semibold text-white hover:bg-action-hover"
        >
          Contact sales
        </Link>
      </div>
    </header>
  );
}