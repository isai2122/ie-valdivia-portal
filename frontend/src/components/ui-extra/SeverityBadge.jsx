import { Badge } from "@/components/ui/badge";
import { clsx } from "clsx";

const MAP = {
  info:     { label: "Info",     cls: "bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30" },
  warning:  { label: "Alerta",   cls: "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/40" },
  critical: { label: "Crítico",  cls: "bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/40" },
};

export function SeverityBadge({ severity = "info", className, "data-testid": testId }) {
  const s = MAP[severity] || MAP.info;
  return (
    <Badge
      variant="outline"
      data-testid={testId || `severity-${severity}`}
      className={clsx(
        "border-transparent px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
        s.cls, className,
      )}
    >
      <span className={clsx(
        "mr-1 inline-block h-1.5 w-1.5 rounded-full",
        severity === "info" && "bg-sky-400",
        severity === "warning" && "bg-amber-400",
        severity === "critical" && "bg-rose-400 animate-pulse",
      )} />
      {s.label}
    </Badge>
  );
}
