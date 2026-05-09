import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Satellite, Lock, Mail, Loader2, Wind, Radar, CircuitBoard } from "lucide-react";

import { useAuth } from "@/lib/auth/context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().email("Correo inválido"),
  password: z.string().min(1, "Contraseña requerida"),
});

const DEMO = [
  ["admin@metanosrgan.co", "Admin123!", "admin"],
  ["analista@metanosrgan.co", "Analista123!", "analyst"],
  ["visor@metanosrgan.co", "Visor123!", "viewer"],
];

const SHOW_DEMO = (process.env.REACT_APP_SHOW_DEMO_USERS || "true").toLowerCase() === "true";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [submitting, setSubmitting] = useState(false);

  const {
    register, handleSubmit, setValue, formState: { errors },
  } = useForm({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });

  const onSubmit = async ({ email, password }) => {
    setSubmitting(true);
    try {
      await login(email, password);
      toast.success("Bienvenido a METAvision");
      const to = loc.state?.from && loc.state.from !== "/login" ? loc.state.from : "/overview";
      nav(to, { replace: true });
    } catch (e) {
      toast.error(e.message || "Credenciales inválidas");
    } finally {
      setSubmitting(false);
    }
  };

  const fillDemo = (e, p) => { setValue("email", e); setValue("password", p); };

  return (
    <div className="grid min-h-screen grid-cols-1 bg-slate-950 text-slate-100 lg:grid-cols-2" data-testid="login-page">
      {/* LEFT — branding */}
      <aside className="relative hidden overflow-hidden lg:block" data-testid="login-branding">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,#10b98122,transparent_55%),radial-gradient(ellipse_at_bottom_right,#0ea5e933,transparent_55%)]" />
        <div className="absolute inset-0 opacity-[0.06] [background-image:linear-gradient(#94a3b8_1px,transparent_1px),linear-gradient(90deg,#94a3b8_1px,transparent_1px)] [background-size:40px_40px]" />
        <div className="relative flex h-full flex-col justify-between px-14 py-16">
          <div>
            <div className="flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-emerald-500/10 ring-1 ring-emerald-400/30">
                <Satellite className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.24em] text-emerald-400/80">METAvision</div>
                <div className="text-xs text-slate-500">v0.2 · Fase 2</div>
              </div>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <h1 className="text-5xl font-semibold leading-[1.05] tracking-tight text-slate-50">
              Detectando lo<br />invisible.<br />
              <span className="text-emerald-400">Protegiendo</span> el<br />Magdalena Medio.
            </h1>
            <p className="mt-6 max-w-md text-sm text-slate-400">
              Dashboard de inteligencia geoespacial que integra Sentinel-5P, viento y mapas de
              infraestructura crítica para rastrear plumas de metano hasta su origen.
            </p>

            <ul className="mt-8 space-y-3">
              {[
                [Radar, "IA de superresolución CH₄ (MetanoSRGAN Elite v2.1)"],
                [Wind, "Campos de viento e infraestructura integrados"],
                [CircuitBoard, "Alertas en tiempo real por WebSocket"],
              ].map(([Ic, t]) => (
                <li key={t} className="flex items-center gap-3 text-sm text-slate-300">
                  <span className="grid h-8 w-8 place-items-center rounded-md bg-slate-900/80 ring-1 ring-slate-800">
                    <Ic className="h-4 w-4 text-emerald-400" />
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </motion.div>

          <p className="text-xs text-slate-600">
            © 2026 METAvision · Colombia · Motor IA: MetanoSRGAN Elite v2.1
          </p>
        </div>
      </aside>

      {/* RIGHT — form */}
      <section className="relative flex items-center justify-center px-6 py-12" data-testid="login-form-side">
        <div className="absolute inset-0 opacity-[0.04] [background-image:linear-gradient(#94a3b8_1px,transparent_1px),linear-gradient(90deg,#94a3b8_1px,transparent_1px)] [background-size:40px_40px] lg:hidden" />
        <div className="relative w-full max-w-md">
          <div className="mb-8 lg:hidden">
            <div className="font-mono text-xs uppercase tracking-[0.22em] text-emerald-400/80">METAvision</div>
            <div className="mt-1 text-xl font-semibold">Dashboard de Inteligencia Geoespacial del Metano</div>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-7 shadow-[0_0_0_1px_rgba(16,185,129,0.06),0_20px_80px_-20px_rgba(16,185,129,0.15)] backdrop-blur">
            <div className="mb-6">
              <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">Acceso autorizado</div>
              <h2 className="mt-1 text-2xl font-semibold text-slate-50">Iniciar sesión</h2>
              <p className="mt-1 text-sm text-slate-400">Usa tus credenciales corporativas.</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" data-testid="login-form">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-300">Correo</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input
                    id="email" type="email" autoComplete="email"
                    placeholder="tu@metanosrgan.co"
                    className="border-slate-700 bg-slate-950/60 pl-9 text-slate-100 placeholder:text-slate-500 focus-visible:ring-emerald-500/40"
                    data-testid="login-email-input"
                    {...register("email")}
                  />
                </div>
                {errors.email && <p className="text-xs text-rose-400" data-testid="login-email-error">{errors.email.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-300">Contraseña</Label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <Input
                    id="password" type="password" autoComplete="current-password"
                    placeholder="••••••••"
                    className="border-slate-700 bg-slate-950/60 pl-9 text-slate-100 placeholder:text-slate-500 focus-visible:ring-emerald-500/40"
                    data-testid="login-password-input"
                    {...register("password")}
                  />
                </div>
                {errors.password && <p className="text-xs text-rose-400" data-testid="login-password-error">{errors.password.message}</p>}
              </div>

              <Button
                type="submit" disabled={submitting}
                className="w-full bg-emerald-500 text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
                data-testid="login-submit-button"
              >
                {submitting ? (<><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Iniciando…</>) : "Ingresar"}
              </Button>
            </form>

            {SHOW_DEMO && (
              <details className="mt-6 text-sm text-slate-400" data-testid="login-demo-accordion">
                <summary className="cursor-pointer select-none text-slate-400 hover:text-emerald-400">
                  Credenciales demo
                </summary>
                <div className="mt-3 space-y-2 rounded-lg border border-slate-800 bg-slate-950/60 p-3 font-mono text-xs">
                  {DEMO.map(([e, p, r]) => (
                    <button
                      key={e}
                      type="button"
                      onClick={() => fillDemo(e, p)}
                      className="flex w-full items-center justify-between rounded px-2 py-1 text-left hover:bg-slate-800/70"
                      data-testid={`login-demo-${r}`}
                    >
                      <span className="text-slate-300">{e}</span>
                      <span className="text-emerald-400/90">{p}</span>
                    </button>
                  ))}
                </div>
              </details>
            )}
          </div>

          <p className="mt-6 text-center text-[11px] text-slate-600">
            METAvision v0.2 · Motor IA: MetanoSRGAN Elite v2.1
          </p>
        </div>
      </section>
    </div>
  );
}
