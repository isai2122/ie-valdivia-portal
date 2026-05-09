import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { clsx } from "clsx";
import { Card } from "@/components/ui/card";

export function KpiCard({
  title, value, hint, delta, trend,
  icon: Icon, tone = "emerald", className,
  "data-testid": testId,
}) {
  const toneRing = {
    emerald: "ring-emerald-500/10 text-emerald-400",
    sky:     "ring-sky-500/10 text-sky-400",
    amber:   "ring-amber-500/10 text-amber-400",
    rose:    "ring-rose-500/10 text-rose-400",
  }[tone];

  const deltaCls =
    trend === "up"   ? "text-emerald-400" :
    trend === "down" ? "text-rose-400"    : "text-slate-400";
  const DeltaIcon = trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : Minus;

  return (
    <Card
      data-testid={testId || "kpi-card"}
      className={clsx(
        "relative overflow-hidden border-slate-800/80 bg-slate-900/60 p-5 transition hover:border-slate-700 hover:bg-slate-900/80",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
            {title}
          </div>
          <div className="mt-2 text-3xl font-semibold tracking-tight text-slate-50">
            {value}
          </div>
          {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
        </div>
        {Icon && (
          <div className={clsx("grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-950 ring-1", toneRing)}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      {delta != null && (
        <div className={clsx("mt-4 inline-flex items-center gap-1 text-xs font-medium", deltaCls)}>
          <DeltaIcon className="h-3.5 w-3.5" />
          <span>{delta}</span>
        </div>
      )}
    </Card>
  );
}
