"use server";

import { updateTag } from "next/cache";
import { cookies } from "next/headers";
import { apiGet } from "@/lib/api";

// The cache labels admin screens may refresh. Add to this list as screens are built.
const ALLOWED_TAGS = new Set(["site-settings", "homepage", "products", "categories", "industries"]);

// Server Actions can be called by anyone who can reach the site, so first ask FastAPI
// whether the caller really has a valid signed-in session.
export async function refreshPublicSite(tags: string[]): Promise<void> {
  const token = (await cookies()).get("access_token")?.value;
  if (!token) throw new Error("Not signed in");

  await apiGet("/api/v1/auth/me", {
    headers: { Cookie: `access_token=${token}` },
    cache: "no-store",
  }); // throws unless the session is valid

  for (const tag of tags) {
    if (ALLOWED_TAGS.has(tag)) updateTag(tag);
  }
}