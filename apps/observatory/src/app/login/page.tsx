"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const REASONS: Record<string, string> = {
  operator_session_required: "Sign in to reach the Brain.",
  operator_auth_not_configured:
    "This deployment has no operator access key set. Set OBSERVATORY_ACCESS_KEY and OBSERVATORY_SESSION_SECRET, then redeploy.",
};

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const reason = params.get("reason") || "";
  const next = params.get("next") || "/";

  const [accessKey, setAccessKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const unconfigured = reason === "operator_auth_not_configured";

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ access_key: accessKey }),
      });
      if (res.ok) {
        // Full navigation, so middleware re-runs with the new cookie.
        window.location.href = next.startsWith("/") ? next : "/";
        return;
      }
      const body = await res.json().catch(() => ({}));
      setError(
        body?.detail === "operator_auth_not_configured"
          ? REASONS.operator_auth_not_configured
          : "That access key was not recognized."
      );
    } catch {
      setError("Could not reach the sign-in service. Check your connection and try again.");
    } finally {
      setSubmitting(false);
      router.refresh();
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-cockpit-bg px-4 py-16">
      <div className="w-full max-w-sm space-y-5">
        <div className="space-y-1.5">
          <h1 className="text-base font-semibold tracking-tight text-cockpit-text">
            Brain Observatory
          </h1>
          <p className="text-xs leading-relaxed text-cockpit-muted">
            {REASONS[reason] || "Sign in to reach the Brain."}
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="space-y-3 rounded-lg border border-cockpit-border bg-cockpit-panel p-4"
        >
          <label className="block space-y-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-cockpit-muted">
              Operator access key
            </span>
            <input
              type="password"
              value={accessKey}
              onChange={(e) => setAccessKey(e.target.value)}
              autoComplete="current-password"
              autoFocus
              disabled={unconfigured || submitting}
              className="w-full rounded border border-cockpit-border bg-cockpit-bg px-2.5 py-2 font-mono text-sm text-cockpit-text outline-none focus:border-cockpit-accent focus-visible:ring-1 focus-visible:ring-cockpit-accent disabled:opacity-50"
            />
          </label>

          {error && (
            <p role="alert" className="text-xs leading-relaxed text-cockpit-red">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={unconfigured || submitting || !accessKey}
            className="w-full rounded bg-cockpit-accent px-3 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-cockpit-accent focus-visible:ring-offset-2 focus-visible:ring-offset-cockpit-bg disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-[10px] leading-relaxed text-cockpit-muted">
          Sessions last 12 hours. The Brain API key stays on the server and is never
          sent to your browser.
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
