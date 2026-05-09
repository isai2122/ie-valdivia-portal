import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { SeverityBadge } from "./SeverityBadge";
import { useWs } from "@/lib/ws/context";
import { timeAgo } from "@/lib/format";

export function NotificationsBell() {
  const { recent } = useWs();
  const nav = useNavigate();
  const unread = recent.length;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className="relative inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-800 bg-slate-900/60 text-slate-300 hover:text-slate-100 hover:border-slate-700"
          aria-label="Notificaciones"
          data-testid="notifications-bell"
        >
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span
              className="absolute -right-1 -top-1 flex min-h-[16px] min-w-[16px] items-center justify-center rounded-full bg-emerald-500 px-1 text-[10px] font-semibold text-slate-950"
              data-testid="notifications-badge"
            >
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-96 border-slate-800 bg-slate-950 p-0 text-slate-200"
        data-testid="notifications-popover"
      >
        <div className="flex items-center justify-between px-4 py-3">
          <div className="text-sm font-medium">Alertas en tiempo real</div>
          <button
            className="text-xs text-emerald-400 hover:underline"
            onClick={() => nav("/alerts")}
            data-testid="notifications-see-all"
          >
            Ver todas
          </button>
        </div>
        <Separator className="bg-slate-800" />
        <ScrollArea className="max-h-80">
          {recent.length === 0 && (
            <div className="px-4 py-10 text-center text-xs text-slate-500">
              Sin alertas nuevas desde que iniciaste sesión.
            </div>
          )}
          {recent.slice(0, 8).map((a) => (
            <button
              key={a.id}
              onClick={() => nav(`/alerts?id=${a.id}`)}
              className="block w-full px-4 py-3 text-left hover:bg-slate-900/80"
              data-testid={`notification-item-${a.id}`}
            >
              <div className="flex items-start gap-3">
                <SeverityBadge severity={a.severity} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-slate-100">{a.title}</div>
                  <div className="mt-0.5 line-clamp-2 text-xs text-slate-400">{a.message}</div>
                  <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">
                    {timeAgo(a.created_at)}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
