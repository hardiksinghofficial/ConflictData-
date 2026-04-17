import React, { useState, useEffect } from 'react';
import { Target, TrendingUp, Clock } from 'lucide-react';

const ConflictRollup = () => {
  const [conflicts, setConflicts] = useState([]);

  useEffect(() => {
    const fetchConflicts = async () => {
      try {
        const res = await fetch('https://hardik1231312-conflictdata.hf.space/api/v1/active-conflicts');
        const data = await res.json();
        setConflicts(data || []);
      } catch (err) {
        console.error("Conflict Hub Error:", err);
      }
    };
    fetchConflicts();
    const interval = setInterval(fetchConflicts, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '15px', borderBottom: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Target size={18} color="var(--accent-red)" />
        <span style={{ fontWeight: 700, fontSize: '13px', letterSpacing: '1px' }}>ACTIVE CONFLICT HUB</span>
      </div>

      <div style={{ flex: 1, padding: '10px', overflowY: 'auto' }}>
        {conflicts.map(c => (
          <div key={c.conflict_id} className="glass-panel" style={{ padding: '15px', marginBottom: '10px', background: 'rgba(255,255,255,0.02)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
              <span>{c.countries?.join(', ') || 'Global'}</span>
              <span style={{ color: c.intensity === 'WAR' ? 'var(--accent-red)' : 'var(--accent-amber)' }}>{c.intensity}</span>
            </div>
            <div style={{ fontWeight: 700, fontSize: '14px', marginBottom: '12px' }}>{c.name}</div>
            
            {/* Intensity Bar */}
            <div style={{ background: '#1e293b', height: '4px', borderRadius: '2px', position: 'relative', overflow: 'hidden', marginBottom: '8px' }}>
              <div style={{ 
                background: c.intensity === 'WAR' ? 'var(--accent-red)' : 'var(--accent-amber)', 
                width: `${Math.min(100, (c.total_events / 20) * 100)}%`, 
                height: '100%',
                transition: 'width 1s ease'
              }}></div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-secondary)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <TrendingUp size={10} /> {c.total_events} EVENTS
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={10} /> {new Date(c.last_event_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}
        {conflicts.length === 0 && <div style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '20px', fontSize: '12px' }}>NO ACTIVE WARS DETECTED</div>}
      </div>
    </div>
  );
};

export default ConflictRollup;
