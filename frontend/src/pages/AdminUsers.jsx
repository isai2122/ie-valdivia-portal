import { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";

import { api } from "@/lib/api";
import { PageHeader } from "@/components/ui-extra/PageHeader";
import { RoleBadge } from "@/components/ui-extra/RoleBadge";
import { StatusBadge } from "@/components/ui-extra/StatusBadge";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

const FALLBACK = [
  { id: "seed-admin",   email: "admin@metanosrgan.co",    name: "Isai Admin",    role: "admin",   active: true },
  { id: "seed-analyst", email: "analista@metanosrgan.co", name: "Ana Lista",     role: "analyst", active: true },
  { id: "seed-viewer",  email: "visor@metanosrgan.co",    name: "Vicente Visor", role: "viewer",  active: true },
];

export default function AdminUsers() {
  const [users, setUsers] = useState(null);  // null = cargando, arr = datos, "fallback" = banner
  const [source, setSource] = useState("live"); // "live" | "fallback"

  useEffect(() => {
    const ctrl = new AbortController();
    api.get("/admin/users", { signal: ctrl.signal })
      .then((r) => { setUsers(r.data || []); setSource("live"); })
      .catch(() => { setUsers(FALLBACK); setSource("fallback"); });
    return () => ctrl.abort();
  }, []);

  return (
    <div className="mx-auto max-w-[1440px] px-6 py-8" data-testid="admin-users-page">
      <PageHeader
        kicker="Sistema"
        title="Usuarios"
        subtitle="Gestión de identidades y roles del dashboard."
      />

      {source === "fallback" && (
        <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-200" data-testid="admin-fallback-banner">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-medium">Endpoint pendiente</div>
            <div className="mt-1 text-amber-300/80">
              No se pudo consultar <code className="font-mono">GET /api/admin/users</code>. Mostrando los 3 usuarios
              semilla conocidos. Cuando el endpoint esté disponible, esta vista se llenará con datos reales.
            </div>
          </div>
        </div>
      )}

      <Card className="border-slate-800/80 bg-slate-900/60" data-testid="admin-users-card">
        {users === null ? (
          <div className="space-y-2 p-4">{Array.from({length: 4}).map((_, i) => <Skeleton key={i} className="h-10 bg-slate-900/80" />)}</div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-transparent">
                  <TableHead className="text-xs text-slate-500">Email</TableHead>
                  <TableHead className="text-xs text-slate-500">Nombre</TableHead>
                  <TableHead className="text-xs text-slate-500">Rol</TableHead>
                  <TableHead className="text-xs text-slate-500">Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id} className="border-slate-800 hover:bg-slate-900/60" data-testid={`user-row-${u.email}`}>
                    <TableCell className="font-mono text-xs text-slate-300">{u.email}</TableCell>
                    <TableCell className="text-sm text-slate-200">{u.name}</TableCell>
                    <TableCell><RoleBadge role={u.role} /></TableCell>
                    <TableCell><StatusBadge status={u.active ? "active" : "suspended"} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}
