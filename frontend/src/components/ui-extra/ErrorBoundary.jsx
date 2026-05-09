import React from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw, LogOut } from "lucide-react";

export class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error("[ErrorBoundary]", error, info); }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="grid min-h-screen place-items-center bg-slate-950 px-6 text-slate-100" data-testid="error-boundary">
        <div className="max-w-md text-center">
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-rose-400">Error inesperado</div>
          <h1 className="mt-2 text-3xl font-semibold">Algo falló.</h1>
          <p className="mt-2 text-sm text-slate-400">
            Se produjo un error al renderizar esta vista. Puedes reintentar o cerrar sesión.
          </p>
          <pre className="mt-4 max-h-40 overflow-auto rounded-md border border-slate-800 bg-slate-900/60 p-3 text-left text-xs text-rose-200">
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <div className="mt-5 flex justify-center gap-2">
            <Button onClick={() => window.location.reload()} className="bg-emerald-500 text-slate-950 hover:bg-emerald-400">
              <RefreshCw className="mr-2 h-4 w-4" /> Reintentar
            </Button>
            <Button
              variant="outline"
              onClick={() => { localStorage.removeItem("msrgan_token"); window.location.href = "/login"; }}
              className="border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800"
            >
              <LogOut className="mr-2 h-4 w-4" /> Salir
            </Button>
          </div>
        </div>
      </div>
    );
  }
}
