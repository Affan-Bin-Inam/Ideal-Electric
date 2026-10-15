import Link from "next/link";
import { getSiteSettings } from "@/lib/site-settings";
import { telHref, whatsappHref } from "@/lib/contact";

export async function SiteFooter() {
  const s = await getSiteSettings();

  const phones = [s.phone_primary, s.phone_secondary].filter((p): p is string => Boolean(p));
  const whatsapp = whatsappHref(s.whatsapp_number);
  const socials = [
    { label: "Facebook", href: s.facebook_url },
    { label: "Instagram", href: s.instagram_url },
    { label: "LinkedIn", href: s.linkedin_url },
  ].filter((x): x is { label: string; href: string } => Boolean(x.href));
  const address = [s.address_line, s.city].filter(Boolean).join(", ");

  const heading = "text-xs font-semibold uppercase tracking-wider text-brand-yellow";
  const link = "hover:text-white hover:underline";

  return (
    <footer className="bg-ink text-sm text-white/70">
      <div className="h-1 bg-gradient-to-r from-brand-green via-brand-yellow to-brand-red" />
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-3">
        <div>
          <p className="text-lg font-semibold text-white">{s.company_name}</p>
          {s.tagline && <p className="mt-1 text-white">{s.tagline}</p>}
          {s.about_short && <p className="mt-3 max-w-sm">{s.about_short}</p>}
        </div>

        <div>
          <p className={heading}>Explore</p>
          <ul className="mt-3 space-y-2">
            <li><Link href="/products" className={link}>Products</Link></li>
            <li><Link href="/industries" className={link}>Industries</Link></li>
            <li><Link href="/contact" className={link}>Contact</Link></li>
          </ul>
        </div>

        <div>
          <p className={heading}>Contact</p>
          <ul className="mt-3 space-y-2">
            {address && (
              <li>
                {address}
                {s.google_maps_url && (
                  <>
                    {" "}
                    <a href={s.google_maps_url} target="_blank" rel="noopener noreferrer" className={link}>
                      (map)
                    </a>
                  </>
                )}
              </li>
            )}
            {phones.map((p) => {
              const href = telHref(p);
              return (
                <li key={p}>
                  {href ? <a href={href} className={link}>{p}</a> : p}
                </li>
              );
            })}
            {whatsapp && (
              <li>
                <a href={whatsapp} target="_blank" rel="noopener noreferrer" className={link}>
                  WhatsApp
                </a>
              </li>
            )}
            {s.email_sales && (
              <li>
                <a href={`mailto:${s.email_sales}`} className={link}>{s.email_sales}</a>
              </li>
            )}
            {s.business_hours && <li className="whitespace-pre-line">{s.business_hours}</li>}
          </ul>

          {socials.length > 0 && (
            <ul className="mt-4 flex gap-4">
              {socials.map((x) => (
                <li key={x.label}>
                  <a href={x.href} target="_blank" rel="noopener noreferrer" className={link}>
                    {x.label}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="border-t border-white/10 py-4 text-center text-xs">
        © {s.company_name}. All rights reserved.
      </div>
    </footer>
  );
}