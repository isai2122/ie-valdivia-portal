import { Link } from "react-router-dom";
import { ShieldOff } from "lucide-react";

export default function Forbidden() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-950 text-slate-200" data-testid="forbidden-page">
      <div className="text-center">
        <div className="grid h-12 w-12 mx-auto place-items-center rounded-full bg-rose-500/10 ring-1 ring-rose-500/30">
          <ShieldOff className="h-5 w-5 text-rose-400" />
        </div>
        <div className="mt-4 font-mono text-xs uppercase tracking-[0.25em] text-rose-400/80">Error 403</div>
        <h1 className="mt-2 text-4xl font-semibold">Acceso restringido</h1>
        <p className="mt-2 max-w-md text-sm text-slate-400">
          Tu rol actual no tiene permisos para ver esta sección. Si crees que es un error, contacta a un administrador.
        </p>
        <Link
          to="/overview"
          data-testid="forbidden-home-link"
          className="mt-6 inline-block rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400"
        >
          Volver al Overview
        </Link>
      </div>
    </div>
  );
}
