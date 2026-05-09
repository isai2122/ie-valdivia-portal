import { Badge } from "@/components/ui/badge";
import { clsx } from "clsx";

const MAP = {
  new:       { label: "Nuevo",       cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30" },
  reviewed:  { label: "Revisado",    cls: "bg-slate-500/15 text-slate-300  ring-slate-500/30" },
  dismissed: { label: "Descartado",  cls: "bg-zinc-500/15  text-zinc-300   ring-zinc-500/30"  },
  queued:    { label: "En cola",     cls: "bg-sky-500/15   text-sky-300    ring-sky-500/30"   },
  running:   { label: "Procesando",  cls: "bg-amber-500/15 text-amber-300  ring-amber-500/30" },
  done:      { label: "Completado",  cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30" },
  failed:    { label: "Fallido",     cls: "bg-rose-500/15  text-rose-300   ring-rose-500/30"  },
  active:    { label: "Activo",      cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30" },
  suspended: { label: "Suspendido",  cls: "bg-amber-500/15 text-amber-300  ring-amber-500/30" },
  abandoned: { label: "Abandonado",  cls: "bg-zinc-500/15  text-zinc-400   ring-zinc-500/30"  },
  maintenance: { label: "Mant.",     cls: "bg-amber-500/15 text-amber-300  ring-amber-500/30" },
  retired:   { label: "Retirado",    cls: "bg-zinc-500/15  text-zinc-400   ring-zinc-500/30"  },
};

export function StatusBadge({ status = "new", className, "data-testid": testId }) {
  const s = MAP[status] || { label: status, cls: "bg-slate-500/15 text-slate-300 ring-slate-500/30" };
  return (
    <Badge
      variant="outline"
      data-testid={testId || `status-${status}`}
      className={clsx("border-transparent px-2 py-0.5 text-[11px] font-medium ring-1", s.cls, className)}
    >
      {s.label}
    </Badge>
  );
}
