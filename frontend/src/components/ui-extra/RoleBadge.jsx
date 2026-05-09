import { Badge } from "@/components/ui/badge";
import { clsx } from "clsx";

const MAP = {
  admin:   { label: "Admin",    cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40" },
  analyst: { label: "Analista", cls: "bg-sky-500/15     text-sky-300     ring-sky-500/40" },
  viewer:  { label: "Visor",    cls: "bg-slate-500/15   text-slate-300   ring-slate-500/40" },
};

export function RoleBadge({ role = "viewer", className, "data-testid": testId }) {
  const r = MAP[role] || MAP.viewer;
  return (
    <Badge
      variant="outline"
      data-testid={testId || `role-${role}`}
      className={clsx("border-transparent px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ring-1", r.cls, className)}
    >
      {r.label}
    </Badge>
  );
}
