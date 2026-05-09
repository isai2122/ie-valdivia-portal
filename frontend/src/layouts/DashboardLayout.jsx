import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard, Map as MapIcon, Bell, BarChart3, Cpu, Upload,
  ShieldCheck, Users, FileSearch, Settings, Satellite, ChevronsLeft, ChevronsRight,
  LogOut, User, Palette, MapPin,
} from "lucide-react";
import { toast } from "sonner";
import { clsx } from "clsx";

import { useAuth } from "@/lib/auth/context";
import { useWs } from "@/lib/ws/context";
import { api } from "@/lib/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ConnectionDot } from "@/components/ui-extra/ConnectionDot";
import { NotificationsBell } from "@/components/ui-extra/NotificationsBell";
import { RoleBadge } from "@/components/ui-extra/RoleBadge";
import { CommandPalette } from "@/components/ui-extra/CommandPalette";

const NAV_OPERACION = [
  { to: "/overview",  label: "Overview", icon: LayoutDashboard },
  { to: "/map",       label: "Mapa",     icon: MapIcon },
  { to: "/alerts",    label: "Alertas",  icon: Bell, hasBadge: true },
  { to: "/analytics", label: "Análisis", icon: BarChart3 },
];
const NAV_IA = [
  { to: "/model",     label: "Modelo",   icon: Cpu },
  { to: "/inference", label: "Ingesta",  icon: Upload },
];
const NAV_SISTEMA = [
  { to: "/admin/users",  label: "Usuarios",      icon: Users,       roles: ["admin"] },
  { to: "/admin/audit",  label: "Auditoría",     icon: FileSearch,  roles: ["admin"], placeholder: true },
  { to: "/admin/settings", label: "Configuración", icon: Settings,  roles: ["admin"], placeholder: true },
];

const BREADCRUMB_MAP = {
  "/overview": "Overview",
  "/map": "Mapa",
  "/alerts": "Alertas",
  "/analytics": "Análisis",
  "/model": "Modelo IA",
  "/inference": "Ingesta",
  "/admin/users": "Usuarios",
  "/admin/audit": "Auditoría",
  "/admin/settings": "Configuración",
};

function NavItem({ to, label, icon: Icon, collapsed, badge, placeholder, testId }) {
  return (
    <NavLink
      to={to}
      end={to === "/overview"}
      data-testid={testId}
      className={({ isActive }) => clsx(
        "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
        isActive
          ? "bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/20"
          : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
      {!collapsed && placeholder && (
        <span className="ml-auto rounded-full border border-slate-700 px-1.5 py-[1px] font-mono text-[9px] uppercase tracking-wider text-slate-500">
          soon
        </span>
      )}
      {!collapsed && badge != null && badge > 0 && (
        <span className="ml-auto inline-flex min-h-[18px] min-w-[18px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-semibold text-slate-950">
          {badge > 99 ? "99+" : badge}
        </span>
      )}
      {collapsed && badge != null && badge > 0 && (
        <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-emerald-400" />
      )}
    </NavLink>
  );
}

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const { state: wsState } = useWs();
  const nav = useNavigate();
  const loc = useLocation();

  const [collapsed, setCollapsed] = useState(false);
  const [unackCount, setUnackCount] = useState(0);
  const [stations, setStations] = useState([]);

  // Breadcrumb derivado de la ruta actual
  const current = Object.entries(BREADCRUMB_MAP).find(([k]) => loc.pathname.startsWith(k))?.[1]
    || loc.pathname.replace("/", "") || "Inicio";

  // Cargar unack count + stations para sidebar/palette
  const refreshUnack = async () => {
    try {
      const r = await api.get("/alerts?acknowledged=false&limit=500");
      setUnackCount(Array.isArray(r.data) ? r.data.length : 0);
    } catch { /* silenciar */ }
  };

  useEffect(() => {
    let mounted = true;
    refreshUnack();
    api.get("/stations").then((r) => { if (mounted) setStations(r.data || []); }).catch(() => {});
    const iv = setInterval(refreshUnack, 30000);
    return () => { mounted = false; clearInterval(iv); };
  }, []);

  const onLogout = async () => {
    await logout();
    toast.success("Sesión cerrada");
    nav("/login", { replace: true });
  };

  const initials = (user?.name || "?").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100" data-testid="dashboard-layout">
      {/* Sidebar */}
      <aside
        className={clsx(
          "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-slate-800/80 bg-slate-950/90 transition-[width] duration-200 md:flex",
          collapsed ? "w-[68px]" : "w-64",
        )}
        data-testid="sidebar"
      >
        {/* Logo + toggle */}
        <div className="flex items-center gap-3 border-b border-slate-800/60 px-3 py-4">
          <Link to="/overview" className="flex items-center gap-3 overflow-hidden">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-500/10 ring-1 ring-emerald-400/30">
              <Satellite className="h-4 w-4 text-emerald-400" />
            </div>
            {!collapsed && (
              <div className="leading-tight">
                <div className="text-sm font-semibold tracking-wide">METAvision</div>
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-400/80">
                  IA · MetanoSRGAN v2.1
                </div>
              </div>
            )}
          </Link>
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="ml-auto inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-500 hover:bg-slate-800/60 hover:text-slate-200"
            data-testid="sidebar-toggle"
            aria-label={collapsed ? "Expandir" : "Colapsar"}
          >
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <SectionLabel collapsed={collapsed}>Operación</SectionLabel>
          {NAV_OPERACION.map((i) => (
            <NavItem
              key={i.to}
              {...i}
              collapsed={collapsed}
              badge={i.hasBadge ? unackCount : undefined}
              testId={`sidebar-link-${i.label.toLowerCase()}`}
            />
          ))}

          <SectionLabel collapsed={collapsed} className="mt-5">IA & Datos</SectionLabel>
          {NAV_IA.map((i) => (
            <NavItem key={i.to} {...i} collapsed={collapsed} testId={`sidebar-link-${i.label.toLowerCase()}`} />
          ))}

          {user?.role === "admin" && (
            <>
              <SectionLabel collapsed={collapsed} className="mt-5" data-testid="sidebar-section-sistema">
                Sistema
              </SectionLabel>
              {NAV_SISTEMA.map((i) => (
                <NavItem key={i.to} {...i} collapsed={collapsed} testId={`sidebar-link-${i.label.toLowerCase()}`} />
              ))}
            </>
          )}
        </nav>

        {/* Footer sidebar — usuario */}
        <div className="border-t border-slate-800/60 px-2 py-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-slate-800/60"
                data-testid="sidebar-user-button"
              >
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-emerald-500/10 text-[11px] font-semibold text-emerald-300">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                {!collapsed && (
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{user?.name}</div>
                    <div className="mt-0.5"><RoleBadge role={user?.role} /></div>
                  </div>
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="top" align="start" className="w-56 border-slate-800 bg-slate-950 text-slate-200">
              <DropdownMenuLabel className="text-slate-500">{user?.email}</DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-slate-800" />
              <DropdownMenuItem className="focus:bg-slate-800" data-testid="user-menu-profile">
                <User className="mr-2 h-4 w-4" /> Mi perfil
                <span className="ml-auto text-[10px] uppercase text-slate-600">soon</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="focus:bg-slate-800"
                onSelect={() => toast.message("Tema oscuro activo. Light mode en Fase 5.")}
                data-testid="user-menu-theme"
              >
                <Palette className="mr-2 h-4 w-4" /> Cambiar tema
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-slate-800" />
              <DropdownMenuItem
                className="text-rose-300 focus:bg-rose-500/10 focus:text-rose-200"
                onSelect={onLogout}
                data-testid="user-menu-logout"
              >
                <LogOut className="mr-2 h-4 w-4" /> Cerrar sesión
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar */}
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-4 border-b border-slate-800/80 bg-slate-950/80 px-4 backdrop-blur md:px-6" data-testid="topbar">
          {/* Breadcrumbs */}
          <div className="flex min-w-0 items-center gap-2 text-sm" data-testid="breadcrumbs">
            <Link to="/overview" className="text-slate-500 hover:text-slate-300">METAvision</Link>
            <span className="text-slate-700">/</span>
            <span className="truncate font-medium text-slate-200">{current}</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Selector zona (estático por ahora) */}
            <div className="hidden md:block">
              <Select defaultValue="magdalena_medio">
                <SelectTrigger
                  className="h-8 w-44 border-slate-800 bg-slate-900/60 text-xs text-slate-300"
                  data-testid="zone-select"
                >
                  <MapPin className="mr-1.5 h-3.5 w-3.5 text-emerald-400" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-slate-800 bg-slate-950 text-slate-200">
                  <SelectItem value="magdalena_medio">Magdalena Medio</SelectItem>
                  <SelectItem value="llanos" disabled>Llanos Orientales · próximo</SelectItem>
                  <SelectItem value="caribe" disabled>Costa Caribe · próximo</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <ConnectionDot state={wsState} />
            <NotificationsBell />
          </div>
        </header>

        {/* Contenido con transición */}
        <main className="min-w-0 flex-1" data-testid="main-content">
          <AnimatePresence mode="wait">
            <motion.div
              key={loc.pathname}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <CommandPalette stations={stations} />
    </div>
  );
}

function SectionLabel({ children, collapsed, className, "data-testid": testId }) {
  if (collapsed) return <div className={clsx("my-2 border-t border-slate-800/50", className)} data-testid={testId} />;
  return (
    <div
      className={clsx("px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-600", className)}
      data-testid={testId}
    >
      {children}
    </div>
  );
}
