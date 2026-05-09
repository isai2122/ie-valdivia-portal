import React, { useState, useEffect, useRef } from 'react';
import {
  Activity, AlertTriangle, Zap, TrendingUp, Radio, Clock,
  RefreshCw, Download, Eye, EyeOff, Bell, Settings
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useQuery } from '@/hooks/useTRPC';
import { GeoMap } from '@/components/GeoMap';

export function CommandCenter() {
  const [darkMode, setDarkMode] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [liveAlerts, setLiveAlerts] = useState([]);
  const [systemStatus, setSystemStatus] = useState('operational');
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const wsRef = useRef(null);

  // Obtener datos de tRPC
  const { data: statsData, loading: statsLoading } = useQuery('stats.overview', {});
  const { data: alertsData, loading: alertsLoading } = useQuery('alerts.recent', {});
  const { data: stationsData, loading: stationsLoading } = useQuery('stations.list', {});

  // Conectar a WebSocket para alertas en tiempo real
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          setWsConnected(true);
          console.log('WebSocket conectado');
        };

        wsRef.current.onmessage = (event) => {
          try {
            const alert = JSON.parse(event.data);
            setLiveAlerts(prev => [alert, ...prev.slice(0, 9)]);
            setLastUpdate(new Date());
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setWsConnected(false);
        };

        wsRef.current.onclose = () => {
          setWsConnected(false);
          // Reconectar en 5 segundos
          setTimeout(connectWebSocket, 5000);
        };
      } catch (e) {
        console.error('WebSocket connection error:', e);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Usar alertas de tRPC si no hay WebSocket
  useEffect(() => {
    if (!wsConnected && alertsData && alertsData.length > 0) {
      setLiveAlerts(alertsData.slice(0, 10));
    }
  }, [alertsData, wsConnected]);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-900 text-red-100';
      case 'high':
        return 'bg-orange-900 text-orange-100';
      case 'medium':
        return 'bg-yellow-900 text-yellow-100';
      default:
        return 'bg-blue-900 text-blue-100';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'operational':
        return 'text-green-400';
      case 'warning':
        return 'text-yellow-400';
      case 'critical':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className={`min-h-screen transition-colors ${darkMode ? 'bg-slate-950 text-slate-50' : 'bg-slate-50 text-slate-950'}`}>
      {/* Header */}
      <div className={`border-b ${darkMode ? 'border-slate-800' : 'border-slate-200'} p-4 sticky top-0 z-10 backdrop-blur`}>
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
            <h1 className="text-2xl font-bold">Centro de Comando MetanoSRGAN</h1>
            <Badge className={`ml-4 ${wsConnected ? 'bg-green-900' : 'bg-red-900'}`}>
              {wsConnected ? '🟢 En Línea' : '🔴 Fuera de Línea'}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setDarkMode(!darkMode)}
              className="text-slate-400 hover:text-slate-200"
            >
              {darkMode ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:text-slate-200"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 space-y-6">
        {/* KPIs en Tiempo Real */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className={`p-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Detecciones Activas</p>
                <p className="text-3xl font-bold text-green-400">{statsData?.total_detections || 0}</p>
              </div>
              <Activity className="w-8 h-8 text-green-500" />
            </div>
          </Card>

          <Card className={`p-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Alertas Críticas</p>
                <p className="text-3xl font-bold text-red-400">{statsData?.critical_alerts || 0}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
          </Card>

          <Card className={`p-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">PPB Promedio</p>
                <p className="text-3xl font-bold text-yellow-400">{statsData?.avg_ppb?.toFixed(0) || 0}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-yellow-500" />
            </div>
          </Card>

          <Card className={`p-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white'}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Estaciones Monitoreadas</p>
                <p className="text-3xl font-bold text-blue-400">{stationsData?.length || 0}</p>
              </div>
              <Radio className="w-8 h-8 text-blue-500" />
            </div>
          </Card>
        </div>

        {/* Mapa Geoespacial */}
        <Card className={`p-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white'}`}>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            Mapa de Calor Geoespacial
          </h2>
          <GeoMap />
        </Card>

        {/* Panel de Alertas en Tiempo Real */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className={`lg:col-span-2 p-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white'}`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Bell className="w-5 h-5 text-red-500" />
                Alertas en Tiempo Real
              </h2>
              <Button
                variant="ghost"
                size="sm"
                className="text-slate-400 hover:text-slate-200"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>

            <div className="space-y-2 max-h-96 overflow-y-auto">
              {liveAlerts.length > 0 ? (
                liveAlerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border-l-4 ${getSeverityColor(alert.severity || 'high')} ${darkMode ? 'bg-slate-800' : 'bg-slate-50'}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-sm">{alert.station}</p>
                        <p className="text-xs opacity-75">{alert.message || `PPB: ${alert.ppb?.toFixed(1) || 'N/A'}`}</p>
                        <p className="text-xs opacity-50 mt-1">
                          <Clock className="w-3 h-3 inline mr-1" />
                          {new Date(alert.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                      <Badge className={getSeverityColor(alert.severity || 'high')}>
                        {alert.severity?.toUpperCase() || 'ALERT'}
                      </Badge>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-slate-400">
                  <p>No hay alertas en tiempo real</p>
                </div>
              )}
            </div>
          </Card>

          {/* Panel de Estado del Sistema */}
          <Card className={`p-4 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white'}`}>
            <h2 className="text-lg font-semibold mb-4">Estado del Sistema</h2>
            <div className="space-y-3">
              <div>
                <p className="text-sm text-slate-400">Backend API</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor('operational')}`} />
                  <span className="text-sm font-medium">Operacional</span>
                </div>
              </div>

              <div>
                <p className="text-sm text-slate-400">Base de Datos</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor('operational')}`} />
                  <span className="text-sm font-medium">Conectada</span>
                </div>
              </div>

              <div>
                <p className="text-sm text-slate-400">WebSocket</p>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(wsConnected ? 'operational' : 'warning')}`} />
                  <span className="text-sm font-medium">{wsConnected ? 'En Línea' : 'Reconectando...'}</span>
                </div>
              </div>

              <div>
                <p className="text-sm text-slate-400">Última Actualización</p>
                <p className="text-xs text-slate-300 mt-1">{lastUpdate.toLocaleTimeString()}</p>
              </div>

              <Button className="w-full mt-4 bg-blue-600 hover:bg-blue-700">
                <Download className="w-4 h-4 mr-2" />
                Descargar Reporte
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
