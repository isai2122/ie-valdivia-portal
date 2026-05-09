import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { BarChart3, Bell, Cpu, LayoutDashboard, Map as MapIcon, ShieldCheck, Upload } from "lucide-react";

export function CommandPalette({ stations = [] }) {
  const [open, setOpen] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const go = (path) => { setOpen(false); nav(path); };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="overflow-hidden p-0 bg-slate-950 border-slate-800 max-w-xl"
        data-testid="command-palette"
      >
        <Command className="bg-transparent">
          <CommandInput placeholder="Buscar páginas, estaciones, acciones…" />
          <CommandList>
            <CommandEmpty>Sin resultados.</CommandEmpty>
            <CommandGroup heading="Navegación">
              <CommandItem onSelect={() => go("/overview")} data-testid="cmd-item-overview">
                <LayoutDashboard className="mr-2 h-4 w-4" /> Overview
              </CommandItem>
              <CommandItem onSelect={() => go("/map")} data-testid="cmd-item-map">
                <MapIcon className="mr-2 h-4 w-4" /> Mapa geoespacial
              </CommandItem>
              <CommandItem onSelect={() => go("/alerts")} data-testid="cmd-item-alerts">
                <Bell className="mr-2 h-4 w-4" /> Alertas
              </CommandItem>
              <CommandItem onSelect={() => go("/analytics")} data-testid="cmd-item-analytics">
                <BarChart3 className="mr-2 h-4 w-4" /> Análisis
              </CommandItem>
              <CommandItem onSelect={() => go("/model")} data-testid="cmd-item-model">
                <Cpu className="mr-2 h-4 w-4" /> Modelo IA
              </CommandItem>
              <CommandItem onSelect={() => go("/inference")} data-testid="cmd-item-inference">
                <Upload className="mr-2 h-4 w-4" /> Ingesta
              </CommandItem>
              <CommandItem onSelect={() => go("/admin/users")} data-testid="cmd-item-admin">
                <ShieldCheck className="mr-2 h-4 w-4" /> Usuarios (admin)
              </CommandItem>
            </CommandGroup>
            {stations.length > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup heading="Estaciones">
                  {stations.map((s) => (
                    <CommandItem
                      key={s.id}
                      onSelect={() => go(`/map?station=${s.id}`)}
                      data-testid={`cmd-station-${s.id}`}
                    >
                      <MapIcon className="mr-2 h-4 w-4 text-emerald-400" />
                      <span>{s.name}</span>
                      <span className="ml-auto text-[10px] uppercase tracking-wider text-slate-500">{s.department}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
