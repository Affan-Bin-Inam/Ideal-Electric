"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { AdminApiError, adminFetch } from "@/lib/admin-api";
import type { AdminUser } from "@/lib/admin-types";

type Session = { user: AdminUser; logout: () => Promise<void> };
const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside AdminShell");
  return session;
}

// Add an entry here whenever a new admin screen exists.
const NAV = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/inquiries", label: "Inquiries" },
  { href: "/admin/settings", label: "Site settings" },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    adminFetch<AdminUser>("/api/v1/auth/me")
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch((error) => {
        if (cancelled) return;
        if (error instanceof AdminApiError && error.status === 401) {
          router.replace("/admin/login");
        } else {
          setProblem("We couldn't reach the server. Check that it is running, then reload.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function logout() {
    try {
      await adminFetch("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // even if the call fails, leave the admin area
    }
    router.replace("/admin/login");
  }

  if (problem) {
    return (
      <p role="alert" className="p-8 text-center text-action">
        {problem}
      </p>
    );
  }
  if (!user) {
    return (
      <p role="status" className="p-8 text-center text-muted">
        Checking your session…
      </p>
    );
  }

  return (
    <SessionContext.Provider value={{ user, logout }}>
      <div className="min-h-screen bg-surface md:grid md:grid-cols-[14rem_1fr]">
        <aside className="bg-ink text-white md:flex md:flex-col">
          <div className="px-4 py-4 text-sm font-semibold">
            Ideal Electric <span className="text-brand-yellow">Admin</span>
          </div>
          <nav
            aria-label="Admin"
            className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-1 md:flex-col md:overflow-visible"
          >
            {NAV.map((item) => {
              const active =
                item.href === "/admin" ? pathname === "/admin" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`whitespace-nowrap rounded px-3 py-2 text-sm ${
                    active
                      ? "bg-white/15 font-semibold"
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="border-t border-white/10 px-4 py-3 text-xs text-white/70">
            <p className="truncate">{user.email}</p>
            <button onClick={logout} className="mt-2 font-semibold text-white hover:underline">
              Sign out
            </button>
          </div>
        </aside>
        <main className="min-w-0 p-6">{children}</main>
      </div>
    </SessionContext.Provider>
  );
}