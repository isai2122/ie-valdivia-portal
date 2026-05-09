import React from 'react';
import { TrendingUp, AlertCircle, Clock, Download, Database } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useQuery } from '@/hooks/useTRPC';

export function Predictions() {
  const { data: recurrenceData, loading } = useQuery('analytics.recurrence', {});

  if (loading) return <div className="p-8 text-center text-slate-400">Analizando 409 eventos reales del Magdalena Medio...</div>;

  const getRiskColor = (level) => {
    switch (level) {
      case 'Crítico': return 'bg-red-900 text-red-100';
      case 'Alto': return 'bg-orange-900 text-orange-100';
      default: return 'bg-blue-900 text-blue-100';
    }
  };

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-50">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Database className="text-blue-400" />
            Análisis de Recurrencia Real v5.2
          </h1>
          <p className="text-slate-400">Basado exclusivamente en datos históricos de Sentinel-5P</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="border-slate-700 hover:bg-slate-800" onClick={() => window.open('/api/trpc/export.geojson', '_blank')}>
            <Download className="w-4 h-4 mr-2" />
            Descargar GeoJSON Real
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Ranking de Recurrencia */}
        <Card className="lg:col-span-2 p-6 bg-slate-900 border-slate-800">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <AlertCircle className="text-red-500" />
            Ranking de Recurrencia por Estación
          </h2>
          <div className="space-y-4">
            {recurrenceData?.station_recurrence_ranking?.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between p-4 bg-slate-800 rounded-lg border border-slate-700">
                <div>
                  <p className="font-bold text-lg">{item.station}</p>
                  <p className="text-sm text-slate-400">
                    {item.event_count} eventos detectados | Promedio: {item.avg_ppb} ppb
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-mono text-blue-400">{item.recurrence_rate}%</p>
                  <Badge className={getRiskColor(item.risk_level)}>{item.risk_level}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Resumen de Datos Reales */}
        <Card className="p-6 bg-slate-900 border-slate-800">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="text-green-500" />
            Resumen de Datos
          </h2>
          <div className="space-y-6">
            <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-center">
              <p className="text-sm text-slate-400">Total Eventos Procesados</p>
              <p className="text-4xl font-bold text-white">{recurrenceData?.total_real_events || 0}</p>
            </div>
            
            <div className="space-y-2">
              <p className="text-sm font-medium">Fuente de Información</p>
              <div className="p-3 bg-blue-900/20 border border-blue-800 rounded text-xs text-blue-200">
                {recurrenceData?.data_source}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800">
              <p className="text-xs text-slate-500 italic">
                Este análisis se genera procesando la base de datos maestra de eventos reales. No se utilizan modelos de dispersión simulados ni datos externos no verificados.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
