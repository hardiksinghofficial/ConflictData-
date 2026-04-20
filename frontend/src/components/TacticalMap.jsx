import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Target, Shield, Zap, MapPin, Activity, AlertTriangle, Users } from 'lucide-react';

const createRadarIcon = (severity, color = '#f43f5e') => {
  const size = severity > 8 ? 20 : 14;
  return L.divIcon({
    className: 'custom-radar-icon',
    html: `
      <div style="position: relative; width: ${size}px; height: ${size}px;">
        <div class="radar-ring" style="border-color: ${color}"></div>
        <div style="
          position: absolute; top: 0; left: 0; width: 100%; height: 100%;
          background: ${color}; border-radius: 50%; box-shadow: 0 0 15px ${color}; z-index: 2;
        "></div>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2]
  });
};

const createCivilianIcon = () => {
  return L.divIcon({
    className: 'civilian-risk-icon',
    html: `
      <div style="position: relative; width: 18px; height: 18px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #ef4444; box-shadow: 0 0 15px rgba(239, 68, 68, 0.4)">
         <div style="width: 2px; height: 8px; background: #ef4444; border-radius: 1px;"></div>
      </div>
    `,
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  });
};

const TacticalMap = ({ events, layerData, selectedEvent, layers }) => {
  const navigate = useNavigate();

  const handleAnalyzeSector = (ev) => {
    const context = `Analyze specifically this event: ${ev.title} in ${ev.city}, ${ev.country}. Type: ${ev.event_type}. Severity: ${ev.severity_score}. Note: ${ev.notes}`;
    navigate('/sitrep', { state: { context } });
  };
  
  // Calculate Surge Centroids from Trend Data + Ongoing Events
  const surgeMarkers = useMemo(() => {
    if (!layerData.trends || !events) return [];
    return layerData.trends.map(trend => {
       const countryEvents = events.filter(e => e.country_iso3 === trend.country_iso3);
       if (countryEvents.length === 0) return null;
       const avgLat = countryEvents.reduce((s, e) => s + e.lat, 0) / countryEvents.length;
       const avgLon = countryEvents.reduce((s, e) => s + e.lon, 0) / countryEvents.length;
       return { ...trend, lat: avgLat, lon: avgLon };
    }).filter(Boolean);
  }, [layerData.trends, events]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <MapContainer 
        center={[20, 10]} 
        zoom={3} 
        style={{ height: '100%', width: '100%', background: '#020203' }}
        zoomControl={false}
      >
        {layers.satellite.active ? (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution='&copy; ESRI'
            className="satellite-filtered"
            opacity={layers.satellite.opacity}
          />
        ) : (
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; CARTO'
          />
        )}
        
        {/* STRATEGIC BATTLE FRONTS */}
        {layers.frontlines.active && (layerData.frontlines || []).map((f, i) => (
          <Circle 
            key={`front-${i}`}
            center={[f.lat, f.lon]}
            radius={200000}
            pathOptions={{ 
              color: '#f43f5e', fillColor: '#ef4444', 
              fillOpacity: layers.frontlines.opacity,
              dashArray: '10, 15', weight: 2
            }}
          >
             <Popup className="tactical-popup">
                <div style={{ padding: '15px' }}>
                   <div style={{ color: 'var(--accent-red)', fontWeight: 900, fontSize: '10px', letterSpacing: '2px' }}>ACTIVE FRONTLINE</div>
                   <div style={{ fontSize: '15px', fontWeight: 800, color: 'white', margin: '6px 0' }}>{f.country} SECTION</div>
                   <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Engagement Type: {f.primary_engagement}</div>
                </div>
             </Popup>
          </Circle>
        ))}

        {/* TACTICAL HOTSPOTS (HEATMAP) */}
        {layers.hotspots.active && (layerData.hotspots || []).map((h, i) => (
          <Circle 
            key={`hot-${i}`}
            center={[h.lat, h.lon]}
            radius={350000}
            pathOptions={{ 
              color: 'transparent', fillColor: '#f43f5e', 
              fillOpacity: layers.hotspots.opacity, weight: 0
            }}
          />
        ))}

        {/* SURGE VECTORS (TREND ANALYTICS) */}
        {layers.surges.active && surgeMarkers.map((s, i) => (
           <Circle 
             key={`surge-${i}`}
             center={[s.lat, s.lon]}
             radius={500000}
             pathOptions={{ 
               color: 'var(--accent-amber)', fillColor: 'var(--accent-amber)', 
               fillOpacity: layers.surges.opacity * 0.5, weight: 1, dashArray: '5, 5'
             }}
           >
              <Popup className="tactical-popup">
                 <div style={{ padding: '15px' }}>
                    <div style={{ color: 'var(--accent-amber)', fontWeight: 900, fontSize: '10px' }}>CONFLICT SURGE DETECTED</div>
                    <div style={{ fontSize: '18px', fontWeight: 900, color: 'white' }}>+{s.surge_percentage}%</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>ISO-ALPHA3: {s.country_iso3}</div>
                 </div>
              </Popup>
           </Circle>
        ))}

        {/* CIVILIAN RISK VECTOR */}
        {layers.civilians.active && (events || []).filter(e => e.fatalities_civilians > 0).map(ev => (
          <Marker key={`civ-${ev.event_id}`} position={[ev.lat, ev.lon]} icon={createCivilianIcon()}>
             <Popup className="tactical-popup">
                <div style={{ padding: '15px' }}>
                   <div style={{ color: '#ef4444', fontWeight: 900, fontSize: '10px' }}>CIVILIAN RISK ALERT</div>
                   <div style={{ fontWeight: 800, margin: '6px 0' }}>{ev.fatalities_civilians} Fatalities Reported</div>
                   <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Sector: {ev.city}</div>
                </div>
             </Popup>
          </Marker>
        ))}

        {/* KINETIC FEED (LIVE EVENTS) */}
        {layers.kinetic.active && (events || []).map((ev) => (
          <Marker 
            key={ev.event_id} 
            position={[ev.lat, ev.lon]}
            icon={createRadarIcon(ev.severity_score)}
            opacity={layers.kinetic.opacity}
          >
            <Popup className="tactical-popup">
              <div className="popup-grid">
                <div className="popup-specs" style={{ borderLeft: `4px solid ${ev.severity_score > 8 ? 'var(--accent-red)' : 'var(--accent-amber)'}` }}>
                   <div style={{ fontSize: '9px', fontWeight: 900, color: ev.severity_score > 8 ? 'var(--accent-red)' : 'var(--accent-amber)', letterSpacing: '1.5px' }}>
                    {ev.severity_score > 8 ? 'KINETIC' : 'TACTICAL'}
                   </div>
                   <div style={{ fontSize: '11px', fontWeight: 800, marginTop: '10px', color: 'var(--text-secondary)' }}>SEVERITY</div>
                   <div style={{ fontSize: '20px', fontWeight: 900, color: 'white' }}>{ev.severity_score}</div>
                   <div style={{ fontSize: '11px', fontWeight: 800, marginTop: '20px', color: 'var(--text-secondary)' }}>LOC</div>
                   <div style={{ fontSize: '11px', fontWeight: 800 }}>{ev.country_iso3}</div>
                </div>
                <div className="popup-intel">
                    <div style={{ fontSize: '10px', fontWeight: 800, color: 'var(--accent-cyan)', marginBottom: '8px' }}>[SITREP: ENCRYPTED]</div>
                    <div style={{ fontSize: '14px', fontWeight: 800, color: 'white', lineHeight: '1.3', marginBottom: '12px' }}>{ev.title}</div>
                    
                    {/* ENRICHED TACTICAL DATA */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '15px', padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border-glass)' }}>
                       {ev.actor1 && <div style={{ fontSize: '9px', fontWeight: 800 }}><span style={{ color: 'var(--accent-cyan)' }}>ACTOR:</span> {ev.actor1.toUpperCase()}</div>}
                       {ev.weapon && <div style={{ fontSize: '9px', fontWeight: 800 }}><span style={{ color: 'var(--text-dim)' }}>EQP:</span> {ev.weapon.toUpperCase()}</div>}
                       {ev.fatalities > 0 && <div style={{ fontSize: '9px', fontWeight: 800 }}><span style={{ color: 'var(--accent-red)' }}>KIA:</span> {ev.fatalities}</div>}
                       {ev.notes && <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-dim)', fontStyle: 'italic', borderTop: '1px solid var(--border-glass)', paddingTop: '6px' }}>{ev.notes}</div>}
                    </div>

                    <button className="nav-command-btn active" style={{ width: '100%', justifyContent: 'center' }} onClick={() => handleAnalyzeSector(ev)}>
                       DEEP ANALYZE SECTOR
                    </button>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* STRATEGIC MONITOR (TOP-LEVEL) */}
        {layers.priority.active && (layerData.monitor || []).map((m, i) => (
          <Marker key={`mon-${i}`} position={[m.lat, m.lon]} icon={createRadarIcon(9.5, '#ef4444')}>
            <Popup className="tactical-popup">
              <div style={{ padding: '15px' }}>
                 <div style={{ color: '#ef4444', fontWeight: 900, fontSize: '10px' }}>PRIORITY MONITOR</div>
                 <div style={{ fontWeight: 800, margin: '8px 0' }}>{m.title}</div>
                 <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>HIGH INTENSITY ENGAGEMENT DETECTED</div>
              </div>
            </Popup>
          </Marker>
        ))}

        <MapController selectedEvent={selectedEvent} />
      </MapContainer>

      <style dangerouslySetInnerHTML={{ __html: `
        .satellite-filtered { filter: brightness(0.35) contrast(1.1) saturate(0.4); }
        .radar-ring { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 1px solid; border-radius: 50%; animation: radar-sweep 2s infinite; z-index: 1; }
        @keyframes radar-sweep { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(3.5); opacity: 0; } }
      `}} />
    </div>
  );
};

const MapController = ({ selectedEvent }) => {
    const map = useMap();
    useEffect(() => { map.setMinZoom(2); }, [map]);
    useEffect(() => {
        if (selectedEvent) map.flyTo([selectedEvent.lat, selectedEvent.lon], 7, { duration: 2 });
    }, [selectedEvent, map]);
    return null;
};

export default TacticalMap;
