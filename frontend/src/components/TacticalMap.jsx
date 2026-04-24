import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, useMap } from 'react-leaflet';
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

const TacticalMap = ({ events, layerData, selectedEvent, onDeepAnalyze, layers }) => {
  const [map, setMap] = useState(null);
  
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

        {/* STRATEGIC TENSION VECTORS (Frontier Intelligence) */}
        {useMemo(() => {
          const highIntensity = (events || []).filter(e => e.severity_score > 7.5);
          const vectors = [];
          for (let i = 0; i < highIntensity.length; i++) {
            for (let j = i + 1; j < highIntensity.length; j++) {
              const e1 = highIntensity[i];
              const e2 = highIntensity[j];
              // Connect if same country or same actor (Strategic Handshake)
              if (e1.country_iso3 === e2.country_iso3 || (e1.actor1 && e1.actor1 === e2.actor1)) {
                vectors.push({ id: `${e1.id}-${e2.id}`, coords: [[e1.lat, e1.lon], [e2.lat, e2.lon]] });
              }
            }
          }
          return vectors.slice(0, 8); // Performance limit
        }, [events]).map(v => (
          <Polyline 
            key={`vector-${v.id}`} 
            positions={v.coords} 
            className="tension-vector"
            pathOptions={{ color: 'var(--accent-red)', weight: 1, opacity: 0.3 }}
          />
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
        {layers.kinetic.active && (events || []).map((ev) => {
          const isExact = ev.geo_precision === 1;
          const isCountryFallback = ev.geo_precision === 3;
          const eventColor = ev.severity_score > 8 ? '#f43f5e' : ev.severity_score > 5 ? '#f59e0b' : '#06b6d4';
          
          return (
            <React.Fragment key={ev.event_id}>
              {/* Verified Incident Halo (Frontier Intelligence) */}
              {ev.verification_count > 1 && (
                <Circle 
                  center={[ev.lat, ev.lon]}
                  radius={8000}
                  className="verified-pulse"
                  pathOptions={{ color: 'var(--accent-green)', fillColor: 'var(--accent-green)', fillOpacity: 0.2, weight: 1 }}
                />
              )}

              {/* Uncertainty Zone for non-exact points */}
              {!isExact && (
                <Circle 
                  center={[ev.lat, ev.lon]}
                  radius={isCountryFallback ? 150000 : 45000}
                  pathOptions={{ 
                    color: eventColor,
                    fillOpacity: 0.1,
                    weight: 1,
                    dashArray: '5, 10'
                  }}
                />
              )}

              <Marker 
                position={[ev.lat, ev.lon]}
                icon={createRadarIcon(ev.severity_score, eventColor)}
                opacity={isExact ? 1 : 0.7}
                zIndexOffset={isExact ? 1000 : 500}
              >
                <Popup className="tactical-popup">
                  <div style={{ minWidth: '340px', maxWidth: '380px' }}>
                    {/* THREAT BANNER */}
                    <div style={{ 
                      padding: '12px 16px', 
                      background: `linear-gradient(135deg, ${eventColor}15, transparent)`,
                      borderBottom: `1px solid ${eventColor}30`,
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: eventColor, boxShadow: `0 0 8px ${eventColor}` }}></div>
                        <span style={{ fontSize: '9px', fontWeight: 900, letterSpacing: '2px', color: eventColor }}>
                          {ev.event_type?.toUpperCase() || 'ENGAGEMENT'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
                        {(ev.verification_count || 1) > 1 && (
                          <span style={{ fontSize: '8px', fontWeight: 900, color: '#10b981', background: 'rgba(16,185,129,0.12)', padding: '2px 7px', borderRadius: '3px', border: '1px solid rgba(16,185,129,0.25)' }}>
                            ✓ {ev.verification_count}
                          </span>
                        )}
                        <span style={{ 
                          fontSize: '8px', fontWeight: 900, padding: '2px 7px', borderRadius: '3px',
                          color: isExact ? '#06b6d4' : '#64748b',
                          border: `1px solid ${isExact ? 'rgba(6,182,212,0.3)' : 'rgba(255,255,255,0.08)'}`,
                          background: isExact ? 'rgba(6,182,212,0.08)' : 'rgba(255,255,255,0.03)'
                        }}>
                          {ev.geo_precision === 1 ? 'EXACT' : ev.geo_precision === 2 ? 'ADMIN' : 'APPROX'}
                        </span>
                      </div>
                    </div>

                    {/* TITLE + LOCATION */}
                    <div style={{ padding: '14px 16px 10px' }}>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: 'white', lineHeight: '1.35', marginBottom: '8px' }}>
                        {ev.title}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px', color: '#94a3b8' }}>
                        <MapPin size={10} style={{ opacity: 0.5 }} />
                        {ev.location_raw || ev.admin1 || ev.country_iso3}
                        <span style={{ opacity: 0.3 }}>•</span>
                        {ev.country}
                      </div>
                    </div>

                    {/* SEVERITY + STATS ROW */}
                    <div style={{ padding: '0 16px 14px', display: 'flex', gap: '8px' }}>
                      {/* Severity Gauge */}
                      <div style={{ 
                        flex: 1, padding: '10px', borderRadius: '8px', 
                        background: `linear-gradient(135deg, ${eventColor}08, ${eventColor}03)`,
                        border: `1px solid ${eventColor}20`, textAlign: 'center'
                      }}>
                        <div style={{ fontSize: '22px', fontWeight: 900, color: eventColor, lineHeight: 1 }}>{ev.severity_score}</div>
                        <div style={{ fontSize: '7px', fontWeight: 800, color: '#64748b', letterSpacing: '1.5px', marginTop: '4px' }}>SEVERITY</div>
                      </div>
                      {/* Confidence */}
                      <div style={{ 
                        flex: 1, padding: '10px', borderRadius: '8px', 
                        background: 'rgba(6,182,212,0.04)', border: '1px solid rgba(6,182,212,0.12)', textAlign: 'center'
                      }}>
                        <div style={{ fontSize: '22px', fontWeight: 900, color: '#06b6d4', lineHeight: 1 }}>{Math.round((ev.geo_confidence||0) * 100)}%</div>
                        <div style={{ fontSize: '7px', fontWeight: 800, color: '#64748b', letterSpacing: '1.5px', marginTop: '4px' }}>CONFIDENCE</div>
                      </div>
                      {/* Fatalities */}
                      {ev.fatalities > 0 && (
                        <div style={{ 
                          flex: 1, padding: '10px', borderRadius: '8px', 
                          background: 'rgba(244,63,94,0.05)', border: '1px solid rgba(244,63,94,0.15)', textAlign: 'center'
                        }}>
                          <div style={{ fontSize: '22px', fontWeight: 900, color: '#f43f5e', lineHeight: 1 }}>{ev.fatalities}</div>
                          <div style={{ fontSize: '7px', fontWeight: 800, color: '#64748b', letterSpacing: '1.5px', marginTop: '4px' }}>KIA</div>
                        </div>
                      )}
                    </div>

                    {/* ENTITY PILLS */}
                    {(ev.actor1 || ev.weapon || ev.actor2) && (
                      <div style={{ padding: '0 16px 14px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {ev.actor1 && (
                          <div style={{ fontSize: '9px', fontWeight: 800, color: '#06b6d4', background: 'rgba(6,182,212,0.08)', padding: '4px 10px', borderRadius: '20px', border: '1px solid rgba(6,182,212,0.2)' }}>
                            ⚔ {ev.actor1}
                          </div>
                        )}
                        {ev.actor2 && (
                          <div style={{ fontSize: '9px', fontWeight: 800, color: '#94a3b8', background: 'rgba(255,255,255,0.04)', padding: '4px 10px', borderRadius: '20px', border: '1px solid rgba(255,255,255,0.08)' }}>
                            ⛨ {ev.actor2}
                          </div>
                        )}
                        {ev.weapon && (
                          <div style={{ fontSize: '9px', fontWeight: 800, color: '#fbbf24', background: 'rgba(251,191,36,0.08)', padding: '4px 10px', borderRadius: '20px', border: '1px solid rgba(251,191,36,0.2)' }}>
                            ◈ {ev.weapon}
                          </div>
                        )}
                      </div>
                    )}

                    {/* FOOTER: ANALYZE + META */}
                    <div style={{ 
                      padding: '10px 16px', background: 'rgba(0,0,0,0.25)', borderTop: '1px solid rgba(255,255,255,0.04)',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                    }}>
                      <button 
                        className="nav-command-btn active" 
                        style={{ padding: '6px 14px', fontSize: '9px' }} 
                        onClick={() => onDeepAnalyze(ev)}
                      >
                        INTEL REPORT
                      </button>
                      <span style={{ fontSize: '8px', color: '#475569', fontFamily: 'var(--font-mono)' }}>
                        {ev.source || 'SRC'} • {ev.country_iso3}
                      </span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}

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

        {/* --- STRATEGIC CONFLICT THEATERS (THE BIG RED ZONES) --- */}
        {layers.theaters.active && (layerData.theaters || []).map((t, i) => {
          // Color coding based on intensity and stability
          const isCritical = t.stability_rating < 40 || t.intensity === 'CRISIS';
          const zoneColor = isCritical ? '#f43f5e' : t.stability_rating < 70 ? '#f59e0b' : '#a855f7';
          const pulseClass = isCritical ? 'pulse-heavy' : 'pulse-soft';
          
          return (
            <React.Fragment key={`theater-${t.conflict_id}`}>
              {/* Core Pulse */}
              <Circle 
                center={[t.center_lat, t.center_lon]}
                radius={Math.max(50000, (t.spread_km || 150) * 1000)}
                pathOptions={{ 
                  color: zoneColor, 
                  fillColor: zoneColor, 
                  fillOpacity: layers.theaters.opacity * 0.2,
                  weight: 1,
                  dashArray: '10, 10'
                }}
                className={pulseClass}
              >
                <Popup className="tactical-popup">
                  <div style={{ padding: '10px', minWidth: '220px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                       <div style={{ color: zoneColor, fontWeight: 900, fontSize: '10px', letterSpacing: '1.5px' }}>STRATEGIC THEATER</div>
                       <div style={{ background: zoneColor, color: 'black', padding: '2px 6px', fontSize: '10px', fontWeight: 900, borderRadius: '4px' }}>
                         {t.intensity}
                       </div>
                    </div>
                    <div style={{ fontSize: '18px', fontWeight: 900, color: 'white', marginBottom: '4px' }}>{t.name}</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginBottom: '15px' }}>Sector spread: {Math.round(t.spread_km)}km</div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                       <div>
                          <div style={{ fontSize: '8px', fontWeight: 800, color: 'var(--text-dim)' }}>STABILITY</div>
                          <div style={{ fontSize: '14px', fontWeight: 900, color: zoneColor }}>{Math.round(t.stability_rating)}%</div>
                       </div>
                       <div>
                          <div style={{ fontSize: '8px', fontWeight: 800, color: 'var(--text-dim)' }}>ENGAGEMENTS</div>
                          <div style={{ fontSize: '14px', fontWeight: 900, color: 'white' }}>{t.total_events}</div>
                       </div>
                       <div style={{ gridColumn: 'span 2' }}>
                          <div style={{ fontSize: '8px', fontWeight: 800, color: 'var(--text-dim)' }}>PRIMARY ACTOR</div>
                          <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--accent-cyan)' }}>{t.dominant_actor || 'UNKNOWN'}</div>
                       </div>
                    </div>

                    <div style={{ marginTop: '12px', display: 'flex', gap: '10px', alignItems: 'center', opacity: 0.5 }}>
                       <Activity size={12} className="pulse-dot" />
                       <span style={{ fontSize: '9px', fontWeight: 800 }}>ONGOING KINETIC SIGNATURES DETECTED</span>
                    </div>
                  </div>
                </Popup>
              </Circle>
              {/* Outer Glow Ring */}
              <Circle 
                center={[t.center_lat, t.center_lon]}
                radius={Math.max(50000, (t.spread_km || 150) * 1000) * 1.5}
                pathOptions={{ 
                  color: zoneColor, 
                  fill: false,
                  weight: 0.5,
                  opacity: 0.3,
                  dashArray: '5, 20'
                }}
                className={pulseClass + '-slow'}
              />
            </React.Fragment>
          );
        })}

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
        if (selectedEvent) {
          const zoomLevel = selectedEvent.geo_precision === 1 ? 9 : selectedEvent.geo_precision === 2 ? 6 : 4;
          map.flyTo([selectedEvent.lat, selectedEvent.lon], zoomLevel, { duration: 2 });
        }
    }, [selectedEvent, map]);
    return null;
};

export default TacticalMap;
