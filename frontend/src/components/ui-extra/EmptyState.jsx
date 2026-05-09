import { clsx } from "clsx";

export function EmptyState({ icon: Icon, title, description, action, className, "data-testid": testId = "empty-state" }) {
  return (
    <div
      className={clsx("flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-900/40 px-6 py-14 text-center", className)}
      data-testid={testId}
    >
      {Icon && (
        <div className="mb-4 grid h-12 w-12 place-items-center rounded-full bg-emerald-500/10 ring-1 ring-emerald-400/20">
          <Icon className="h-5 w-5 text-emerald-400" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-slate-400">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
