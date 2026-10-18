import type { Metadata } from "next";
import { InquiryForm } from "@/components/inquiry-form";
import { telHref, whatsappHref } from "@/lib/contact";
import { getSiteSettings } from "@/lib/site-settings";

export const metadata: Metadata = { title: "Contact" };

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

export default async function ContactPage() {
  const s = await getSiteSettings();

  const phones = [s.phone_primary, s.phone_secondary].filter((p): p is string => Boolean(p));
  const whatsapp = whatsappHref(s.whatsapp_number);
  const address = [s.address_line, s.city].filter(Boolean).join(", ");
  const link = "text-action hover:underline";

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Contact sales</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Send us an inquiry, or reach us directly using the details below.
      </p>

      <div className="mt-10 grid gap-12 lg:grid-cols-[1fr_1.4fr]">
        <div className="space-y-6">
          {address && (
            <Detail label="Address">
              <p>{address}</p>
              {s.google_maps_url && (
                <a
                  href={s.google_maps_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={link}
                >
                  Open in Google Maps
                </a>
              )}
            </Detail>
          )}

          {phones.length > 0 && (
            <Detail label="Phone">
              <ul className="space-y-1">
                {phones.map((p) => {
                  const href = telHref(p);
                  return (
                    <li key={p}>
                      {href ? (
                        <a href={href} className={link}>
                          {p}
                        </a>
                      ) : (
                        p
                      )}
                    </li>
                  );
                })}
              </ul>
            </Detail>
          )}

          {whatsapp && (
            <Detail label="WhatsApp">
              <a href={whatsapp} target="_blank" rel="noopener noreferrer" className={link}>
                Message us on WhatsApp
              </a>
            </Detail>
          )}

          {s.email_sales && (
            <Detail label="Email">
              <a href={`mailto:${s.email_sales}`} className={link}>
                {s.email_sales}
              </a>
            </Detail>
          )}

          {s.business_hours && (
            <Detail label="Business hours">
              <p className="whitespace-pre-line">{s.business_hours}</p>
            </Detail>
          )}
        </div>

        <div>
          <h2 className="text-xl font-bold tracking-tight">Send an inquiry</h2>
          <div className="mt-6">
            <InquiryForm />
          </div>
        </div>
      </div>
    </div>
  );
}