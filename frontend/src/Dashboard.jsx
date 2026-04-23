import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Radio, Globe, Zap, AlertTriangle, Menu, FileText, Sliders, Target, Activity, Flame, Wifi, BarChart3, Users, ZapOff } from 'lucide-react';
import TacticalMap from './components/TacticalMap';
import TacticalFeed from './components/TacticalFeed';
import CombatTicker from './components/CombatTicker';
import LayerManager from './components/LayerManager';
import IncidentIntelligenceCard from './components/IncidentIntelligenceCard';
import API_BASE from './config';
import useTacticalWS from './hooks/useTacticalWS';

const Dashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ total_events: 0, active_wars: 0, high_severity: 0 });
  const [events, setEvents] = useState([]);
  const [layerData, setLayerData] = useState({ monitor: [], frontlines: [], hotspots: [], trends: [], theaters: [] });
  const [activePanels, setActivePanels] = useState({ layers: false, feed: true });
  const [flashAlert, setFlashAlert] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [activeIntelEvent, setActiveIntelEvent] = useState(null);
  const [zuluTime, setZuluTime] = useState(new Date().toUTCString());

  // ZULU Clock Interval
  useEffect(() => {
    const timer = setInterval(() => setZuluTime(new Date().toUTCString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Professional Intelligence Layers State
  const [layers, setLayers] = useState({
    kinetic: { active: true, opacity: 1, name: 'Live Engagement Feed', icon: <Target size={14}/>, group: 'tactical', count: 0 },
    theaters: { active: true, opacity: 0.6, name: 'Strategic Conflict Theaters', icon: <Globe size={14}/>, group: 'strategic', count: 0 },
    priority: { active: true, opacity: 1, name: 'Strategic Monitor', icon: <Shield size={14}/>, group: 'tactical', count: 0 },
    frontlines: { active: false, opacity: 0.3, name: 'Combat Frontlines', icon: <Activity size={14}/>, group: 'strategic', count: 0 },
    hotspots: { active: true, opacity: 0.15, name: 'Sustained Hotspots', icon: <Flame size={14}/>, group: 'strategic', count: 0 },
    surges: { active: true, opacity: 0.4, name: 'Surge Vectors', icon: <BarChart3 size={14}/>, group: 'strategic', count: 0 },
    civilians: { active: false, opacity: 0.8, name: 'Civilian Risk', icon: <Users size={14}/>, group: 'surveillance', count: 0 },
    satellite: { active: false, opacity: 1, name: 'Multispectral Ops', icon: <Globe size={14}/>, group: 'surveillance', count: 0 }
  });

  const updateLayer = (key, updates) => {
    setLayers(prev => ({ ...prev, [key]: { ...prev[key], ...updates } }));
  };

  // Real-time Intelligence Hook
  const { status: wsStatus } = useTacticalWS((newEvent) => {
    setEvents(prev => [newEvent, ...prev.slice(0, 99)]);
    if (newEvent.severity_score >= 7.5 || newEvent.priority) {
      setFlashAlert(newEvent);
      setTimeout(() => setFlashAlert(null), 8000);
    }
    setStats(prev => ({ 
      ...prev, 
      total_events: prev.total_events + 1,
      high_severity: newEvent.severity_score >= 8.5 ? prev.high_severity + 1 : prev.high_severity
    }));
    // Update live count for kinetic layer
    updateLayer('kinetic', { count: events.length + 1 });
  });

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const safeFetch = async (url) => {
          try {
            const res = await fetch(url);
            if (!res.ok) return null;
            const data = await res.json();
            return data;
          } catch (e) {
            console.error(`Fetch failed for ${url}:`, e);
            return null;
          }
        };

        const [statsRes, eventsRes, monitorRes, frontRes, hotRes, trendRes, sitrepRes, theaterRes] = await Promise.all([
          safeFetch(`${API_BASE}/api/v1/stats/stats`),
          safeFetch(`${API_BASE}/api/v1/conflicts/ongoing?limit=100`),
          safeFetch(`${API_BASE}/api/v1/intel/monitor`),
          safeFetch(`${API_BASE}/api/v1/intel/frontlines`),
          safeFetch(`${API_BASE}/api/v1/intel/hotspots`),
          safeFetch(`${API_BASE}/api/v1/intel/trends`),
          safeFetch(`${API_BASE}/api/v1/intel/sitrep`),
          safeFetch(`${API_BASE}/api/v1/intel/theaters`)
        ]);

        const ongoingEvents = (eventsRes && eventsRes.data) || [];
        setEvents(ongoingEvents);

        if (statsRes) {
          setStats({ 
            total_events: statsRes.total_events || 0, 
            active_wars: 0, 
            high_severity: statsRes.by_severity?.HIGH || 0,
            sitrep: sitrepRes 
          });
        }
        
        const safeArr = (arr) => Array.isArray(arr) ? arr : [];

        setLayerData({ 
          monitor: safeArr(monitorRes), 
          frontlines: safeArr(frontRes), 
          hotspots: safeArr(hotRes), 
          trends: safeArr(trendRes),
          theaters: safeArr(theaterRes)
        });

        // Sync Layer Counts
        setLayers(prev => ({
          ...prev,
          kinetic: { ...prev.kinetic, count: ongoingEvents.length },
          theaters: { ...prev.theaters, count: safeArr(theaterRes).length },
          priority: { ...prev.priority, count: safeArr(monitorRes).length },
          frontlines: { ...prev.frontlines, count: safeArr(frontRes).length },
          hotspots: { ...prev.hotspots, count: safeArr(hotRes).length },
          surges: { ...prev.surges, count: safeArr(trendRes).length },
          civilians: { ...prev.civilians, count: ongoingEvents.filter(e => e.fatalities_civilians > 0).length }
        }));

      } catch (err) {
        console.error("Dashboard Init Error:", err);
      }
    };
    fetchInitialData();
  }, []);

  const togglePanel = (panel) => setActivePanels(prev => ({ ...prev, [panel]: !prev[panel] }));
  
  const handleSelectEvent = (event) => { 
    setSelectedEvent(event); 
    setActiveIntelEvent(event); // Open the intelligence card automatically
  };

  return (
    <div className="war-room-layout">
      {activePanels.layers && (
        <LayerManager 
          layers={layers} 
          updateLayer={updateLayer} 
          onClose={() => togglePanel('layers')} 
        />
      )}

      {/* HEADER SECTION */}
      <header className="glass-panel" style={{ height: '70px', display: 'flex', alignItems: 'center', padding: '0 30px', justifyContent: 'space-between', zIndex: 110, borderBottom: '1px solid var(--border-glass)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '25px' }}>
          <div style={{ position: 'relative' }}>
             <Shield color="var(--accent-red)" size={32} />
             <div style={{ position: 'absolute', top: -5, right: -5, width: 8, height: 8, background: 'var(--accent-green)', borderRadius: '50%', boxShadow: '0 0 10px var(--accent-green)' }}></div>
          </div>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 900, letterSpacing: '3px', margin: 0 }}>CONFLICT<span style={{ color: 'var(--accent-red)' }}>IQ</span></h1>
            <div style={{ fontSize: '9px', fontWeight: 700, opacity: 0.5, letterSpacing: '1px' }}>GLOBAL MONITORING // LEVEL-4 STRATEGIC</div>
          </div>
        </div>

        <div className="nav-command-group">
          <button className={`nav-command-btn ${activePanels.layers ? 'active' : ''}`} onClick={() => togglePanel('layers')}>
            <Sliders size={14} /> LAYERS
          </button>
          <button className={`nav-command-btn ${activePanels.feed ? 'active' : ''}`} onClick={() => togglePanel('feed')}>
            <Radio size={14} /> NEWS FEED
          </button>
        </div>

        <div style={{ display: 'flex', gap: '40px', alignItems: 'center' }}>
          {/* NEW: STRATEGIC THREAT LEVEL INDICATOR */}
          {stats.sitrep && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <div style={{ textAlign: 'right' }}>
                   <div style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-secondary)' }}>STRATEGIC THREAT LEVEL</div>
                   <div style={{ fontSize: '12px', fontWeight: 900, color: stats.sitrep.intensity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-amber)', letterSpacing: '1px' }}>
                      {stats.sitrep.intensity || 'ANALYZING...'}
                   </div>
                </div>
                <div style={{ 
                  width: '32px', height: '32px', borderRadius: '4px', 
                  background: stats.sitrep.intensity === 'HIGH' ? 'rgba(244, 63, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                  border: `1px solid ${stats.sitrep.intensity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-amber)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  animation: stats.sitrep.intensity === 'HIGH' ? 'pulse-red 2s infinite' : 'none'
                }}>
                  <AlertTriangle size={18} color={stats.sitrep.intensity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-amber)'} style={{ margin: 'auto' }} />
                </div>
            </div>
          )}

          <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '2px' }}>
             <div style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-secondary)' }}>ZULU TIME</div>
             <div style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>{zuluTime.split(' ')[4]}</div>
          </div>
          <div style={{ width: '1px', height: '20px', background: 'var(--border-glass)' }}></div>
          <div style={{ display: 'flex', gap: '30px' }}>
            <StatItem label="COMMS" value={wsStatus} color={wsStatus === 'ONLINE' ? 'var(--accent-green)' : 'var(--accent-red)'} pulse={wsStatus === 'ONLINE'} />
            <StatItem label="INTEL" value={stats.total_events} />
            <StatItem label="KINETIC" value={stats.high_severity} color="var(--accent-red)" />
          </div>
        </div>
      </header>

      {/* MAIN CONTENT AREA */}
      <main className="main-content">
        <div className="scanline"></div>
        <section className="map-viewport">
          <TacticalMap 
            events={events} 
            layerData={layerData} 
            selectedEvent={selectedEvent} 
            onDeepAnalyze={(ev) => setActiveIntelEvent(ev)}
            layers={layers} 
          />
        </section>

        {activeIntelEvent && (
          <IncidentIntelligenceCard 
            event={activeIntelEvent} 
            onClose={() => setActiveIntelEvent(null)}
            onRequestLiveAnalysis={(ev) => {
               // Optional: trigger manual live re-analysis if ever needed
               console.log("Live analysis requested for", ev.event_id);
            }}
          />
        )}

        <div className={`sidebar-feed ${!activePanels.feed ? 'collapsed' : ''}`}>
          <TacticalFeed 
            events={events} 
            selectedId={selectedEvent?.event_id}
            onSelectEvent={handleSelectEvent} 
          />
        </div>
      </main>

      {/* FLASH ALERT */}
      {flashAlert && (
        <div className="glass-panel" style={{ 
          position: 'fixed', top: '85px', right: activePanels.feed ? '435px' : '20px', 
          zIndex: 1000, padding: '20px', 
          borderLeft: '5px solid var(--accent-red)', animation: 'slide-in 0.5s ease-out', width: '340px',
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: '0 20px 50px rgba(0,0,0,0.5)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-red)', fontWeight: 800, fontSize: '11px', letterSpacing: '1px' }}>
            <AlertTriangle size={14} /> TACTICAL FLASH
          </div>
          <div style={{ fontWeight: 800, fontSize: '15px', marginTop: '10px', lineHeight: '1.3' }}>{flashAlert.title}</div>
          <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>{flashAlert.city}, {flashAlert.country}</div>
        </div>
      )}

      {/* FOOTER */}
      <footer className="footer-ticker">
        <CombatTicker events={events} />
      </footer>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes slide-in { from { transform: translateX(120%); } to { transform: translateX(0); } }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
        .pulse-dot { animation: blink 2s infinite; }
      `}} />
    </div>
  );
};

const StatItem = ({ label, value, color, pulse }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
    <div style={{ fontSize: '9px', color: 'var(--text-secondary)', fontWeight: 800, letterSpacing: '1px' }}>{label}</div>
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
       {pulse && <div className="pulse-dot" style={{ width: '4px', height: '4px', borderRadius: '50%', background: color }}></div>}
       <div style={{ fontSize: '14px', fontWeight: 900, fontFamily: 'var(--font-mono)', color: color || 'var(--text-primary)' }}>{value}</div>
    </div>
  </div>
);

export default Dashboard;
