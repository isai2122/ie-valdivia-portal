import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-950 text-slate-200" data-testid="not-found-page">
      <div className="text-center">
        <div className="font-mono text-xs uppercase tracking-[0.25em] text-emerald-400/80">Error 404</div>
        <h1 className="mt-3 text-4xl font-semibold">Ruta no encontrada</h1>
        <p className="mt-2 max-w-md text-sm text-slate-400">La página que buscas no existe o fue movida.</p>
        <Link
          to="/overview"
          data-testid="not-found-home-link"
          className="mt-6 inline-block rounded-md bg-emerald-500 px-4 py-2 text-sm text-slate-950 hover:bg-emerald-400"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
