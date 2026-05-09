import React, { useState } from 'react';
import { BarChart3, AlertTriangle, TrendingUp, Database, Zap } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function BusinessIntelligence() {
  const [activeTab, setActiveTab] = useState('operators');

  // Datos simulados basados en análisis real de 409 eventos
  const operatorComparison = {
    "Cenit Transporte": {
      total_events: 329,
      stations_managed: 4,
      avg_ppb: 2184.23,
      max_ppb: 2318.92,
      critical_alerts: 0,
      efficiency_score: 100.0
    },
    "Ecopetrol": {
      total_events: 80,
      stations_managed: 1,
      avg_ppb: 2195.45,
      max_ppb: 2305.67,
      critical_alerts: 0,
      efficiency_score: 100.0
    }
  };

  const anomalies = [
    { station: "Mariquita", z_score: -2.83, ppb: 2189.10, severity: "Alto" },
    { station: "Vasconia", z_score: 2.45, ppb: 2305.67, severity: "Alto" },
    { station: "Malena", z_score: -2.12, ppb: 2156.34, severity: "Moderado" }
  ];

  const stationPerformance = [
    { station: "Malena", operator: "Cenit", events: 85, risk_score: 0 },
    { station: "Vasconia", operator: "Cenit", events: 78, risk_score: 0 },
    { station: "Barrancabermeja", operator: "Ecopetrol", events: 80, risk_score: 0 },
    { station: "Mariquita", operator: "Cenit", events: 92, risk_score: 0 },
    { station: "Miraflores", operator: "Cenit", events: 74, risk_score: 0 }
  ];

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-50">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <BarChart3 className="text-blue-400" />
            Business Intelligence v5.3
          </h1>
          <p className="text-slate-400">Análisis comparativo de operadoras y detección de anomalías</p>
        </div>
        <Button variant="outline" className="border-slate-700">
          <Download className="w-4 h-4 mr-2" />
          Exportar Reporte
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800">
        {['operators', 'anomalies', 'performance'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab === 'operators' && 'Comparativa de Operadoras'}
            {tab === 'anomalies' && 'Detección de Anomalías'}
            {tab === 'performance' && 'Desempeño por Estación'}
          </button>
        ))}
      </div>

      {/* Operators Tab */}
      {activeTab === 'operators' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {Object.entries(operatorComparison).map(([operator, metrics]) => (
            <Card key={operator} className="p-6 bg-slate-900 border-slate-800">
              <h3 className="text-xl font-bold mb-4">{operator}</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-400">Eventos Procesados</span>
                  <span className="font-bold text-blue-400">{metrics.total_events}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Estaciones Gestionadas</span>
                  <span className="font-bold">{metrics.stations_managed}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">PPB Promedio</span>
                  <span className="font-bold text-yellow-400">{metrics.avg_ppb.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">PPB Máximo</span>
                  <span className="font-bold text-red-400">{metrics.max_ppb.toFixed(1)}</span>
                </div>
                <div className="pt-4 border-t border-slate-800">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Eficiencia</span>
                    <Badge className="bg-green-900 text-green-100">{metrics.efficiency_score}%</Badge>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Anomalies Tab */}
      {activeTab === 'anomalies' && (
        <Card className="p-6 bg-slate-900 border-slate-800">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <AlertTriangle className="text-red-500" />
            Anomalías Detectadas (Z-Score > 2.0)
          </h2>
          <div className="space-y-4">
            {anomalies.map((anom, idx) => (
              <div key={idx} className="p-4 bg-slate-800 rounded-lg border border-slate-700 flex justify-between items-center">
                <div>
                  <p className="font-bold">{anom.station}</p>
                  <p className="text-sm text-slate-400">Z-Score: {anom.z_score}</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-mono text-yellow-400">{anom.ppb.toFixed(1)} ppb</p>
                  <Badge className={anom.severity === 'Alto' ? 'bg-orange-900 text-orange-100' : 'bg-yellow-900 text-yellow-100'}>
                    {anom.severity}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <Card className="p-6 bg-slate-900 border-slate-800">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <TrendingUp className="text-green-500" />
            Ranking de Desempeño por Estación
          </h2>
          <div className="space-y-3">
            {stationPerformance.map((station, idx) => (
              <div key={idx} className="p-4 bg-slate-800 rounded-lg border border-slate-700 flex justify-between items-center">
                <div>
                  <p className="font-bold">{station.station}</p>
                  <p className="text-sm text-slate-400">{station.operator}</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-blue-400">{station.events} eventos</p>
                  <p className="text-sm text-slate-400">Risk: {station.risk_score}%</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Data Quality Card */}
      <Card className="p-6 bg-slate-900 border-slate-800">
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Database className="text-green-500" />
          Auditoría de Datos
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-slate-800 rounded-lg text-center">
            <p className="text-slate-400">Calidad de Datos</p>
            <p className="text-3xl font-bold text-green-400">100%</p>
          </div>
          <div className="p-4 bg-slate-800 rounded-lg text-center">
            <p className="text-slate-400">Registros Validados</p>
            <p className="text-3xl font-bold text-blue-400">409</p>
          </div>
          <div className="p-4 bg-slate-800 rounded-lg text-center">
            <p className="text-slate-400">Anomalías Detectadas</p>
            <p className="text-3xl font-bold text-yellow-400">31</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
