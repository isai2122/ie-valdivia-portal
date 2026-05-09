import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useQuery } from '@/hooks/useTRPC';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, MapPin, Loader } from 'lucide-react';

// Coordenadas de estaciones del Magdalena Medio
const STATIONS_COORDS = {
  'Vasconia': { lat: 5.8167, lng: -73.3833, name: 'Vasconia (Puerto Boyacá)', operator: 'Cenit' },
  'Mariquita': { lat: 5.2167, lng: -74.9, name: 'Mariquita', operator: 'Cenit' },
  'Barrancabermeja': { lat: 7.0667, lng: -73.85, name: 'Barrancabermeja', operator: 'Ecopetrol' },
  'Malena': { lat: 6.2667, lng: -74.7, name: 'Malena (Puerto Nare)', operator: 'Cenit' },
  'Miraflores': { lat: 5.7, lng: -73.1833, name: 'Miraflores', operator: 'Cenit' }
};

// Colores por intensidad de PPB
const getColorByIntensity = (ppb) => {
  if (ppb > 2300) return '#8B0000'; // Darkred - Crítico
  if (ppb > 2200) return '#FF4500'; // OrangeRed - Muy Alto
  if (ppb > 2100) return '#FFD700'; // Gold - Alto
  if (ppb > 2000) return '#90EE90'; // LightGreen - Moderado
  return '#00AA00'; // Green - Normal
};

const getSeverityLabel = (ppb) => {
  if (ppb > 2300) return 'Crítico';
  if (ppb > 2200) return 'Muy Alto';
  if (ppb > 2100) return 'Alto';
  if (ppb > 2000) return 'Moderado';
  return 'Normal';
};

export function GeoMap() {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const [selectedStation, setSelectedStation] = useState(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Obtener datos de alertas con ubicación geoespacial
  const { data: alertsData, loading: alertsLoading } = useQuery(
    'alerts.heatmap',
    {},
    { enabled: true }
  );

  // Obtener datos de estaciones
  const { data: stationsData, loading: stationsLoading } = useQuery(
    'stations.list',
    {},
    { enabled: true }
  );

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // Inicializar mapa Leaflet centrado en Magdalena Medio
    const map = L.map(mapRef.current).setView([6.0, -73.8], 8);

    // Añadir capa de OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    mapInstanceRef.current = map;
    setMapLoaded(true);

    return () => {
      // Cleanup
    };
  }, []);

  // Actualizar marcadores cuando hay datos de alertas
  useEffect(() => {
    if (!mapInstanceRef.current || !alertsData || alertsLoading) return;

    // Limpiar marcadores anteriores
    Object.values(markersRef.current).forEach(marker => marker.remove());
    markersRef.current = {};

    // Agrupar alertas por estación
    const alertsByStation = {};
    alertsData.forEach(alert => {
      if (!alertsByStation[alert.station]) {
        alertsByStation[alert.station] = [];
      }
      alertsByStation[alert.station].push(alert);
    });

    // Crear marcadores por estación
    Object.entries(alertsByStation).forEach(([station, alerts]) => {
      const coords = STATIONS_COORDS[station];
      if (!coords) return;

      // Calcular PPB máximo para esta estación
      const maxPpb = Math.max(...alerts.map(a => a.ppb || 2000));
      const color = getColorByIntensity(maxPpb);
      const severity = getSeverityLabel(maxPpb);

      // Crear círculo con tamaño proporcional a cantidad de alertas
      const radius = Math.min(alerts.length * 2000, 50000); // Máximo 50km

      const circle = L.circle([coords.lat, coords.lng], {
        color: color,
        fillColor: color,
        fillOpacity: 0.4,
        weight: 3,
        radius: radius,
        popup: `
          <div class="p-3 min-w-max">
            <h3 class="font-bold text-sm">${coords.name}</h3>
            <p class="text-xs text-gray-600">${coords.operator}</p>
            <div class="mt-2 space-y-1">
              <p class="text-xs"><strong>Alertas:</strong> ${alerts.length}</p>
              <p class="text-xs"><strong>PPB Máximo:</strong> ${maxPpb.toFixed(1)}</p>
              <p class="text-xs"><strong>Severidad:</strong> <span class="font-bold" style="color: ${color}">${severity}</span></p>
            </div>
          </div>
        `,
      }).addTo(mapInstanceRef.current);

      // Marcador en el centro
      const marker = L.marker([coords.lat, coords.lng], {
        icon: L.icon({
          iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
          shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
          iconSize: [25, 41],
          iconAnchor: [12, 41],
          popupAnchor: [1, -34],
          shadowSize: [41, 41]
        })
      }).addTo(mapInstanceRef.current);

      marker.bindPopup(circle.getPopup());

      markersRef.current[station] = { circle, marker };

      // Click para seleccionar estación
      circle.on('click', () => setSelectedStation(station));
      marker.on('click', () => setSelectedStation(station));
    });

  }, [alertsData, alertsLoading, mapLoaded]);

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold">Mapa de Calor Geoespacial</h3>
          </div>
          {alertsLoading && <Loader className="w-4 h-4 animate-spin" />}
        </div>

        {/* Mapa */}
        <div
          ref={mapRef}
          className="w-full h-96 rounded-lg border border-gray-200 mb-4"
          style={{ minHeight: '400px' }}
        />

        {/* Leyenda de colores */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#8B0000' }} />
            <span>Crítico (&gt;2300 ppb)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#FF4500' }} />
            <span>Muy Alto (&gt;2200 ppb)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#FFD700' }} />
            <span>Alto (&gt;2100 ppb)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#90EE90' }} />
            <span>Moderado (&gt;2000 ppb)</span>
          </div>
        </div>
      </Card>

      {/* Panel de estación seleccionada */}
      {selectedStation && (
        <Card className="p-4 border-l-4 border-blue-500">
          <h4 className="font-semibold mb-2">{STATIONS_COORDS[selectedStation].name}</h4>
          <div className="space-y-2 text-sm">
            <p><strong>Operador:</strong> {STATIONS_COORDS[selectedStation].operator}</p>
            <p><strong>Coordenadas:</strong> {STATIONS_COORDS[selectedStation].lat.toFixed(4)}°N, {STATIONS_COORDS[selectedStation].lng.toFixed(4)}°W</p>
            {alertsData && (
              <>
                <p><strong>Alertas:</strong> {alertsData.filter(a => a.station === selectedStation).length}</p>
                <p><strong>PPB Promedio:</strong> {(alertsData.filter(a => a.station === selectedStation).reduce((sum, a) => sum + (a.ppb || 0), 0) / alertsData.filter(a => a.station === selectedStation).length).toFixed(1)}</p>
              </>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
