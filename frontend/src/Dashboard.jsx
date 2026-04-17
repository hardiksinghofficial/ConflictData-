import React, { useState, useEffect } from 'react';
import { Shield, Radio, Activity, Globe, Zap, AlertTriangle } from 'lucide-react';
import TacticalMap from './components/TacticalMap';
import AIAnalyst from './components/AIAnalyst';
import ConflictRollup from './components/ConflictRollup';
import CombatTicker from './components/CombatTicker';

const Dashboard = () => {
  const [stats, setStats] = useState({ total_events: 0, active_wars: 0, high_severity: 0 });

  useEffect(() => {
    // Initial fetch for system stats
    const fetchStats = async () => {
      try {
        const res = await fetch('https://hardik1231312-conflictdata.hf.space/api/v1/stats/stats');
        const data = await res.json();
        setStats({
          total_events: data.total_events || 0,
          active_wars: 0, // Will be updated by conflict hub
          high_severity: data.by_severity?.HIGH || 0
        });
      } catch (err) {
        console.error("Dashboard Stats Error:", err);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="war-room-layout">
      {/* Header Overlay */}
      <header className="glass-panel" style={{ gridColumn: '1 / span 3', display: 'flex', alignItems: 'center', padding: '0 20px', justifyContent: 'space-between', zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Shield color="var(--accent-red)" size={32} />
          <h1 style={{ fontSize: '24px', fontWeight: 800, letterSpacing: '1px' }}>CONFLICT<span style={{ color: 'var(--accent-red)' }}>IQ</span></h1>
          <div className="glass-panel" style={{ padding: '4px 12px', fontSize: '12px', color: 'var(--accent-green)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', border: 'none' }}>
            <div className="pulse-red" style={{ background: 'var(--accent-green)', width: '8px', height: '8px' }}></div>
            SYSTEM OPERATIONAL
          </div>
        </div>

        <div style={{ display: 'flex', gap: '30px' }}>
          <StatItem icon={<Globe size={18}/>} label="GLOBAL EVENTS" value={stats.total_events} />
          <StatItem icon={<AlertTriangle size={18} color="var(--accent-red)"/>} label="HIGH INTENSITY" value={stats.high_severity} />
          <StatItem icon={<Zap size={18} color="var(--accent-amber)"/>} label="ACTIVE FRONTS" value="LIVE" />
        </div>
      </header>

      {/* Main Tactical Map */}
      <main className="map-container glass-panel">
        <div className="scanline"></div>
        <TacticalMap />
      </main>

      {/* Intelligence Sidebar */}
      <aside style={{ gridColumn: '1', gridRow: '2' }}>
        <AIAnalyst />
      </aside>

      {/* Conflict Hub Sidebar */}
      <aside style={{ gridColumn: '3', gridRow: '2' }}>
        <ConflictRollup />
      </aside>

      {/* Bottom Ticker */}
      <footer className="glass-panel" style={{ gridColumn: '1 / span 3', gridRow: '3', overflow: 'hidden' }}>
        <CombatTicker />
      </footer>
    </div>
  );
};

const StatItem = ({ icon, label, value }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
    <div style={{ color: 'var(--text-secondary)' }}>{icon}</div>
    <div>
      <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{value}</div>
    </div>
  </div>
);

export default Dashboard;
