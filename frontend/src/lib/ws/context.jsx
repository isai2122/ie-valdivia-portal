/**
 * WsProvider: conexión global al WS /api/ws/alerts cuando hay user.
 * Expone useWs() con estado + lista reciente de alertas + suscripción onAlert().
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/lib/auth/context";
import { TOKEN_KEY } from "@/lib/api";

const WsCtx = createContext(null);
const MAX_RECENT = 50;

function buildWsUrl() {
  const base = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
  const wsBase = base.replace(/^http:/, "ws:").replace(/^https:/, "wss:");
  const tok = encodeURIComponent(localStorage.getItem(TOKEN_KEY) || "");
  return `${wsBase}/api/ws/alerts?token=${tok}`;
}

export function WsProvider({ children }) {
  const { user } = useAuth();
  const [state, setState] = useState("disconnected"); // disconnected | connecting | connected | reconnecting
  const [recent, setRecent] = useState([]);          // últimas alertas recibidas (desc)
  const listenersRef = useRef(new Set());
  const wsRef = useRef(null);
  const retryRef = useRef(0);
  const unmountRef = useRef(false);

  const onAlert = useCallback((fn) => {
    listenersRef.current.add(fn);
    return () => listenersRef.current.delete(fn);
  }, []);

  const connect = useCallback(() => {
    if (unmountRef.current) return;
    if (!user) return;
    if (!localStorage.getItem(TOKEN_KEY)) return;

    setState(retryRef.current > 0 ? "reconnecting" : "connecting");

    let ws;
    try { 
      ws = new WebSocket(buildWsUrl()); 
    } catch (e) { 
      console.error("WS Connection error:", e);
      return scheduleRetry(); 
    }

    wsRef.current = ws;

    ws.onopen = () => { 
      retryRef.current = 0; 
      setState("connected"); 
    };

    ws.onclose = (e) => { 
      console.log("WS Closed:", e.code, e.reason);
      setState("disconnected"); 
      scheduleRetry(); 
    };

    ws.onerror = (e) => { 
      console.error("WS Error:", e);
    };

    ws.onmessage = (ev) => {
      let data; 
      try { 
        data = JSON.parse(ev.data); 
      } catch { 
        return; 
      }
      if (data?.type === "alert.created" && data.alert) {
        setRecent((prev) => [{ ...data.alert, __detection: data.detection, __source: data.source }, ...prev].slice(0, MAX_RECENT));
        listenersRef.current.forEach((fn) => { try { fn(data); } catch { /* */ } });
      }
    };
  }, [user]);

  const scheduleRetry = useCallback(() => {
    if (unmountRef.current) return;
    if (!user) return;
    retryRef.current = Math.min(retryRef.current + 1, 6);
    const delay = Math.min(1000 * 2 ** (retryRef.current - 1), 20000);
    setState("reconnecting");
    setTimeout(() => connect(), delay);
  }, [connect, user]);

  useEffect(() => {
    unmountRef.current = false;
    if (user) connect();
    return () => {
      unmountRef.current = true;
      if (wsRef.current) {
        try { wsRef.current.close(1000, "unmount"); } catch { /* */ }
      }
      wsRef.current = null;
      retryRef.current = 0;
    };
  }, [user?.id, connect]);

  const value = useMemo(() => ({
    state, recent, onAlert,
    _debugDisconnect: () => {
      try { wsRef.current?.close(4000, "manual"); } catch { /* */ }
    },
  }), [state, recent, onAlert]);

  return <WsCtx.Provider value={value}>{children}</WsCtx.Provider>;
}

export function useWs() {
  const ctx = useContext(WsCtx);
  if (!ctx) throw new Error("useWs must be used inside WsProvider");
  return ctx;
}
