// The public address of the site. Set SITE_URL in web/.env.local (and in production)
// once the real domain exists. No trailing slash.
export const SITE_URL = (process.env.SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");