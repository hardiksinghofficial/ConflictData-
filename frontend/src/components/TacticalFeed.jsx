import React from 'react';
import { Crosshair, MapPin, Zap, AlertCircle, Clock, Bomb, Users, ChevronRight } from 'lucide-react';

const TacticalFeed = ({ events, selectedId, onSelectEvent }) => {
  const getCategoryIcon = (type) => {
    const t = type?.toLowerCase() || '';
    if (t.includes('airstrike') || t.includes('shelling')) return <Bomb size={14} color="var(--accent-red)" />;
    if (t.includes('battle') || t.includes('clash')) return <Crosshair size={14} color="var(--accent-red)" />;
    if (t.includes('violence') || t.includes('civilian')) return <Users size={14} color="var(--accent-amber)" />;
    if (t.includes('strategic')) return <Zap size={14} color="var(--accent-green)" />;
    return <AlertCircle size={14} />;
  };

  const getTimeAgo = (timestamp) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'JUST NOW';
    if (diffMins < 60) return `${diffMins}M AGO`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}H AGO`;
    return then.toLocaleDateString();
  };

  // Group events by Relative Date
  const groupEvents = (evs) => {
    const groups = {};
    evs.forEach(ev => {
      const date = new Date(ev.event_time).toLocaleDateString();
      const today = new Date().toLocaleDateString();
      let groupName = date === today ? 'TODAY' : date;
      if (!groups[groupName]) groups[groupName] = [];
      groups[groupName].push(ev);
    });
    return groups;
  };

  const eventGroups = groupEvents(events || []);

  return (
    <div className="sidebar-feed">
      <div style={{ padding: '24px 20px', borderBottom: '1px solid var(--border-glass)', background: 'linear-gradient(to bottom, rgba(255,255,255,0.02), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
           <div style={{ width: '8px', height: '8px', background: 'var(--accent-red)', borderRadius: '50%', animation: 'blink 1.5s infinite' }}></div>
           <h2 style={{ fontSize: '13px', fontWeight: 900, letterSpacing: '2px', color: 'var(--text-primary)' }}>LIVE INTELLIGENCE STREAM</h2>
        </div>
        <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '1px' }}>FEED STATUS: ACTIVE // ENCRYPTED</div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: '20px' }} className="custom-scroller">
        {Object.entries(eventGroups).map(([groupName, groupEvents]) => (
          <div key={groupName}>
            <div className="temporal-header">{groupName}</div>
            {groupEvents.map((ev) => (
              <div 
                key={ev.event_id} 
                className={`feed-card ${selectedId === ev.event_id ? 'active' : ''}`}
                onClick={() => onSelectEvent(ev)}
                style={{ animation: 'slide-in-right 0.3s ease-out' }}
              >
                <div className="impact-bar" style={{ background: ev.severity_score >= 8 ? 'var(--accent-red)' : 'var(--accent-amber)' }}></div>
                
                <div style={{ display: 'flex', gap: '15px' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {getCategoryIcon(ev.event_type)}
                        <span style={{ fontSize: '9px', fontWeight: 900, color: ev.severity_score >= 8 ? 'var(--accent-red)' : 'var(--text-secondary)', letterSpacing: '1px' }}>
                          {ev.event_type?.toUpperCase() || 'GENERAL'}
                        </span>
                      </div>
                      <span style={{ fontSize: '9px', color: 'var(--text-dim)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                        {getTimeAgo(ev.event_time)}
                      </span>
                    </div>

                    <div style={{ fontSize: '13px', fontWeight: 700, lineHeight: '1.45', marginBottom: '8px', color: 'var(--text-primary)' }}>
                      {ev.title}
                    </div>

                    {/* NEW: TACTICAL TELEMETRY BLOCK */}
                    {(ev.actor1 || ev.weapon || ev.fatalities > 0) && (
                      <div style={{ display: 'flex', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' }}>
                        {ev.actor1 && (
                          <div style={{ background: 'rgba(34, 211, 238, 0.1)', border: '1px solid rgba(34, 211, 238, 0.3)', padding: '2px 6px', borderRadius: '3px', fontSize: '8px', fontWeight: 900, color: 'var(--accent-cyan)' }}>
                            ACTOR: {ev.actor1.toUpperCase()}
                          </div>
                        )}
                        {ev.weapon && (
                          <div style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', padding: '2px 6px', borderRadius: '3px', fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)' }}>
                            WEAPON: {ev.weapon.toUpperCase()}
                          </div>
                        )}
                        {ev.fatalities > 0 && (
                          <div style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '2px 6px', borderRadius: '3px', fontSize: '8px', fontWeight: 900, color: 'var(--accent-red)' }}>
                            KIA: {ev.fatalities}
                          </div>
                        )}
                      </div>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 600 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <MapPin size={10} style={{ opacity: 0.5 }} /> {ev.city || 'Sector Unknown'}, {ev.country}
                        </div>
                        
                        {/* UNCERTAINTY BADGE */}
                        <div style={{ 
                          padding: '1px 5px', borderRadius: '4px', fontSize: '8px', fontWeight: 900,
                          color: ev.geo_precision === 1 ? 'var(--accent-cyan)' : 'var(--text-dim)',
                          border: `1px solid ${ev.geo_precision === 1 ? 'var(--accent-cyan)' : 'var(--border-glass)'}`,
                          opacity: 0.7
                        }}>
                          {ev.geo_precision === 1 ? 'EXACT' : ev.geo_precision === 2 ? 'ADMIN-LVL' : 'APPROX'} ({Math.round(ev.geo_confidence * 100)}%)
                        </div>
                      </div>
                      <ChevronRight size={14} style={{ opacity: 0.2 }} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ))}

        {(events || []).length === 0 && (
          <div style={{ padding: '60px 40px', textAlign: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '2px' }}>SIGNAL SCANNING...</div>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', opacity: 0.5, marginTop: '8px' }}>SEEKING KINETIC SIGNATURES</div>
          </div>
        )}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes slide-in-right { from { transform: translateX(10px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
      `}} />
    </div>
  );
};

export default TacticalFeed;
