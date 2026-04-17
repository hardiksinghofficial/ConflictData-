import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in Leaflet
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

// Custom Pulsing Tactical Marker
const createTacticalIcon = (severity) => {
  const size = severity > 8 ? 20 : 12;
  const color = severity > 8 ? '#f43f5e' : '#fbbf24';
  
  return L.divIcon({
    className: 'custom-tactical-icon',
    html: `<div style="
      width: ${size}px; 
      height: ${size}px; 
      background: ${color}; 
      border-radius: 50%; 
      box-shadow: 0 0 10px ${color};
      animation: pulse-red 2s infinite;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2]
  });
};

const TacticalMap = () => {
  const [events, setEvents] = useState([]);
  const [frontlines, setFrontlines] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const ongoingRes = await fetch('https://hardik1231312-conflictdata.hf.space/api/v1/conflicts/ongoing?limit=100');
        const ongoingData = await ongoingRes.json();
        setEvents(ongoingData.data || []);

        const frontlineRes = await fetch('https://hardik1231312-conflictdata.hf.space/api/v1/intel/frontlines');
        const frontlineData = await frontlineRes.json();
        setFrontlines(frontlineData || []);
      } catch (err) {
        console.error("Map Fetch Error:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 45000); // 45s refresh
    return () => clearInterval(interval);
  }, []);

  return (
    <MapContainer 
      center={[20, 10]} 
      zoom={3} 
      style={{ height: '100%', width: '100%', background: '#060608' }}
      zoomControl={false}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
      />
      
      {/* Active Battlefronts (Circles) */}
      {frontlines.map((f, i) => (
        <Circle 
          key={`front-${i}`}
          center={[f.lat, f.lon]}
          radius={120000} // 120km
          pathOptions={{ 
            color: 'var(--accent-red)', 
            fillColor: 'var(--accent-red)', 
            fillOpacity: 0.1,
            dashArray: '5, 10'
          }}
        />
      ))}

      {/* Kinetic Engagement Markers */}
      {events.map((ev) => (
        <Marker 
          key={ev.event_id} 
          position={[ev.lat, ev.lon]}
          icon={createTacticalIcon(ev.severity_score)}
        >
          <Popup className="glass-popup">
            <div style={{ color: 'white', padding: '5px' }}>
              <div style={{ fontSize: '10px', color: 'var(--accent-red)', fontWeight: 800 }}>{ev.event_type?.toUpperCase()}</div>
              <div style={{ fontWeight: 700, margin: '4px 0' }}>{ev.title}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{ev.city}, {ev.country}</div>
              <div style={{ fontSize: '10px', marginTop: '8px', borderTop: '1px solid #333', paddingTop: '4px' }}>
                SEVERITY: <span style={{ color: 'var(--accent-red)' }}>{ev.severity_score}</span> | FATALITIES: {ev.fatalities}
              </div>
            </div>
          </Popup>
        </Marker>
      ))}

      <MapController />
    </MapContainer>
  );
};

// Component to handle map transitions
const MapController = () => {
    const map = useMap();
    useEffect(() => {
        map.setMinZoom(2);
    }, [map]);
    return null;
};

export default TacticalMap;
