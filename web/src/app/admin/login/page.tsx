"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { AdminApiError, adminFetch } from "@/lib/admin-api";

function messageFor(error: unknown): string {
  if (error instanceof AdminApiError) {
    if (error.status === 401) return "Invalid email or password.";
    if (error.status === 429) return "Too many attempts. Please wait a few minutes and try again.";
    if (error.status === 403) return "The server refused this sign-in request.";
  }
  return "Sign-in failed. Please try again.";
}

const inputClass = "mt-1 w-full rounded border border-ink/20 px-3 py-2 text-sm";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError(null);
    setBusy(true);
    try {
      await adminFetch("/api/v1/auth/login", {
        method: "POST",
        json: {
          email: String(data.get("email") ?? "").trim(),
          password: String(data.get("password") ?? ""),
        },
      });
      router.replace("/admin");
    } catch (err) {
      console.error("Sign-in failed:", err); // the details stay in the browser console
      setError(messageFor(err));
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow">
        <Image
          src="/ideal-logo.svg"
          alt="Ideal Electric"
          width={296}
          height={115}
          priority
          className="mx-auto h-14 w-auto"
        />
        <h1 className="mt-6 text-center text-lg font-bold">Admin sign in</h1>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="text-sm font-semibold">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="username"
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="password" className="text-sm font-semibold">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="current-password"
              className={inputClass}
            />
          </div>
          {error && (
            <p role="alert" className="rounded bg-surface px-3 py-2 text-sm text-action">
              {error}
            </p>
          )}
          <button
            disabled={busy}
            className="w-full rounded bg-action px-4 py-3 font-semibold text-white hover:bg-action-hover disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}