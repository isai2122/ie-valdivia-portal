export function PageHeader({ title, subtitle, actions, kicker, "data-testid": testId = "page-header" }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4" data-testid={testId}>
      <div className="min-w-0">
        {kicker && (
          <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
            {kicker}
          </div>
        )}
        <h1 className="truncate text-2xl font-semibold text-slate-50">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
