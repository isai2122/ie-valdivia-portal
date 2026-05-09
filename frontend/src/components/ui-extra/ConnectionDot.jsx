import { clsx } from "clsx";

export function ConnectionDot({ state, className, "data-testid": testId }) {
  const map = {
    connected:    { dot: "bg-emerald-400 shadow-[0_0_0_3px_rgba(16,185,129,.18)]",  label: "Conectado" },
    connecting:   { dot: "bg-sky-400 animate-pulse",  label: "Conectando…" },
    reconnecting: { dot: "bg-amber-400 animate-pulse", label: "Reconectando…" },
    disconnected: { dot: "bg-rose-500",                label: "Desconectado" },
  };
  const s = map[state] || map.disconnected;
  return (
    <div
      className={clsx("inline-flex items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/60 px-2.5 py-1 text-[11px] text-slate-300", className)}
      data-testid={testId || "ws-indicator"}
      data-state={state}
    >
      <span className={clsx("h-2 w-2 rounded-full", s.dot)} />
      <span>{s.label}</span>
    </div>
  );
}
