import React, { useState } from 'react';
import { 
  X, ShieldAlert, Target, Users, MapPin, ExternalLink, 
  Clock, Zap, FileText, ChevronRight, Activity, TrendingUp 
} from 'lucide-react';

const IncidentIntelligenceCard = ({ event, onClose, onRequestLiveAnalysis }) => {
  const [activeTab, setActiveTab] = useState('sitrep');

  if (!event) return null;

  return (
    <div className="incident-intel-card glass-panel shadow-tactical animate-fade-in" style={{
      position: 'absolute',
      top: '20px',
      left: '20px',
      width: '420px',
      maxHeight: 'calc(100vh - 120px)',
      background: 'rgba(5, 7, 12, 0.95)',
      borderRadius: '12px',
      border: '1px solid var(--border-glass)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      color: 'var(--text-primary)'
    }}>
      {/* HEADER */}
      <div style={{
        padding: '15px 20px',
        background: 'rgba(255,255,255,0.03)',
        borderBottom: '1px solid var(--border-glass)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldAlert size={14} color="var(--accent-red)" />
          <span style={{ fontSize: '10px', fontWeight: 900, letterSpacing: '2px', color: 'var(--text-dim)' }}>
            INTEL CASE: {event.event_id?.slice(0, 8)}
          </span>
        </div>
        <button 
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)' }}
        >
          <X size={16} />
        </button>
      </div>

      {/* EVENT CORE INFO */}
      <div style={{ padding: '20px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 900, margin: '0 0 10px 0', lineHeight: '1.3' }}>
          {event.title}
        </h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <MapPin size={12} /> {event.city || 'Sector'}, {event.country}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <Clock size={12} /> {new Date(event.event_time).toLocaleDateString()}
          </div>
          <a 
            href={event.source_url} target="_blank" rel="noreferrer"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--accent-cyan)', textDecoration: 'none' }}
          >
            <ExternalLink size={12} /> VERIFY SOURCE
          </a>
        </div>

        {/* TABS */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glass)', marginBottom: '20px' }}>
          <TabItem active={activeTab === 'sitrep'} label="SITREP" onClick={() => setActiveTab('sitrep')} />
          <TabItem active={activeTab === 'details'} label="ENTITIES" onClick={() => setActiveTab('details')} />
        </div>

        {/* TAB CONTENT: SITREP */}
        {activeTab === 'sitrep' && (
          <div className="tab-content animate-fade-in">
            {event.ai_analysis ? (
              <div style={{ fontSize: '14px', lineHeight: '1.7', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                {event.ai_analysis}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '30px 0', opacity: 0.5 }}>
                <Activity size={32} style={{ marginBottom: '15px' }} />
                <div style={{ fontSize: '11px', fontWeight: 800 }}>NO PRE-STORED ANALYSIS FOUND</div>
                <button 
                  onClick={() => onRequestLiveAnalysis(event)}
                  style={{ 
                    marginTop: '20px', padding: '10px 20px', background: 'var(--accent-cyan)', 
                    color: 'black', border: 'none', borderRadius: '4px', fontSize: '10px', fontWeight: 900,
                    cursor: 'pointer'
                  }}
                >
                  REQUEST LIVE SITREP
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB CONTENT: DETAILS */}
        {activeTab === 'details' && (
          <div className="tab-content animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
              <DetailBox label="PRIMARY ACTOR" value={event.actor1 || 'UNKNOWN'} icon={<Users size={14}/>} />
              <DetailBox label="FATALITIES" value={event.fatalities} color="var(--accent-red)" icon={<Target size={14}/>} />
              <DetailBox label="EQP / WEAPON" value={event.weapon || 'KINETIC'} icon={<Zap size={14}/>} />
              <DetailBox label="ACCURACY" value={`${Math.round(event.geo_confidence * 100)}%`} color="var(--accent-cyan)" />
            </div>
            
            <div className="glass-panel" style={{ padding: '15px', borderRadius: '8px', background: 'rgba(0,0,0,0.2)' }}>
              <div style={{ fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)', letterSpacing: '1px', marginBottom: '8px' }}>TACTICAL NOTES</div>
              <div style={{ fontSize: '12px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                {event.notes || 'No specialized tactical descriptors extracted for this event.'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* FOOTER ACTION */}
      <div style={{ 
        padding: '15px 20px', background: 'rgba(0,0,0,0.3)', borderTop: '1px solid var(--border-glass)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      }}>
         <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }}></div>
            <span style={{ fontSize: '9px', fontWeight: 900, color: 'var(--text-dim)' }}>STORED INTEL ACTIVE</span>
         </div>
         {event.ai_analysis && (
           <button 
             onClick={() => onRequestLiveAnalysis(event)}
             style={{ 
               background: 'none', border: 'none', color: 'var(--accent-cyan)', fontSize: '9px', fontWeight: 900, 
               cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
             }}
           >
             REFRESH ANALYSIS <ChevronRight size={10} />
           </button>
         )}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .tab-content { transition: all 0.3s ease; }
        @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fade-in 0.3s ease-out; }
      `}} />
    </div>
  );
};

const TabItem = ({ active, label, onClick }) => (
  <div 
    onClick={onClick}
    style={{
      padding: '10px 15px',
      fontSize: '11px',
      fontWeight: 900,
      cursor: 'pointer',
      color: active ? 'white' : 'var(--text-dim)',
      borderBottom: active ? '2px solid var(--accent-cyan)' : '2px solid transparent',
      transition: 'all 0.2s'
    }}
  >
    {label}
  </div>
);

const DetailBox = ({ label, value, color, icon }) => (
  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
    <div style={{ fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)', letterSpacing: '1px', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
      {icon} {label}
    </div>
    <div style={{ fontSize: '13px', fontWeight: 900, color: color || 'white', textTransform: 'uppercase' }}>
      {value}
    </div>
  </div>
);

export default IncidentIntelligenceCard;
