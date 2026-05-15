import { useEffect, useState } from "react";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; status: string }
  | { kind: "error"; message: string };

export default function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<{ status: string }>;
      })
      .then((data) => {
        if (!cancelled) setHealth({ kind: "ok", status: data.status });
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : String(err);
        if (!cancelled) setHealth({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-6 py-16">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">home_agent</h1>
        <p className="mt-2 text-slate-600">
          개인용 멀티에이전트 홈 어시스턴트 — 프론트엔드 스캐폴드.
        </p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-medium uppercase tracking-wide text-slate-500">
          Backend status
        </h2>
        <div className="mt-3">
          {health.kind === "loading" && (
            <span className="text-slate-500">Checking…</span>
          )}
          {health.kind === "ok" && (
            <span className="text-emerald-600">● {health.status}</span>
          )}
          {health.kind === "error" && (
            <span className="text-rose-600">● {health.message}</span>
          )}
        </div>
      </section>
    </main>
  );
}
