import "@/App.css";
import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { AuthProviderRoot, ProtectedRoute } from "@/lib/auth/context";
import { WsProvider } from "@/lib/ws/context";
import { ErrorBoundary } from "@/components/ui-extra/ErrorBoundary";

import Login from "@/pages/Login";
import DashboardLayout from "@/layouts/DashboardLayout";

const Overview   = lazy(() => import("@/pages/Overview"));
const MapPage    = lazy(() => import("@/pages/MapPage"));
const Alerts     = lazy(() => import("@/pages/Alerts"));
const Analytics  = lazy(() => import("@/pages/Analytics"));
const Model      = lazy(() => import("@/pages/Model"));
const Inference  = lazy(() => import("@/pages/Inference"));
const AdminUsers = lazy(() => import("@/pages/AdminUsers"));
const Forbidden  = lazy(() => import("@/pages/Forbidden"));
const NotFound   = lazy(() => import("@/pages/NotFound"));

function PageFallback() {
  return (
    <div className="grid min-h-[50vh] place-items-center" data-testid="page-loading">
      <div className="inline-flex items-center gap-3 rounded-full border border-slate-800 bg-slate-900/60 px-4 py-2 text-xs text-slate-400">
        <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" /> Cargando…
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProviderRoot>
          <WsProvider>
            <Suspense fallback={<PageFallback />}>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/403" element={<Forbidden />} />

                <Route element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }>
                  <Route path="/" element={<Navigate to="/overview" replace />} />
                  <Route path="/overview"  element={<Overview />} />
                  <Route path="/map"       element={<MapPage />} />
                  <Route path="/alerts"    element={<Alerts />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/model"     element={<Model />} />
                  <Route path="/inference" element={<Inference />} />

                  <Route path="/admin/users" element={
                    <ProtectedRoute roles={["admin"]}>
                      <AdminUsers />
                    </ProtectedRoute>
                  } />
                  <Route path="/admin/audit"    element={<ProtectedRoute roles={["admin"]}><ComingSoon title="Auditoría" /></ProtectedRoute>} />
                  <Route path="/admin/settings" element={<ProtectedRoute roles={["admin"]}><ComingSoon title="Configuración" /></ProtectedRoute>} />
                </Route>

                <Route path="*" element={<NotFound />} />
              </Routes>
            </Suspense>

            <Toaster
              theme="dark" position="top-right" richColors closeButton
              toastOptions={{
                style: { background: "#0b1220", border: "1px solid #1f2937", color: "#e2e8f0" },
              }}
            />
          </WsProvider>
        </AuthProviderRoot>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

function ComingSoon({ title }) {
  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid={`coming-soon-${title.toLowerCase()}`}>
      <div className="mb-6">
        <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">Sistema</div>
        <h1 className="text-2xl font-semibold text-slate-50">{title}</h1>
      </div>
      <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-14 text-center">
        <p className="text-sm text-slate-400">{title} estará disponible en próximas fases.</p>
      </div>
    </div>
  );
}
