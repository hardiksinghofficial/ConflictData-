import React from 'react';
import { 
  X, ShieldAlert, Target, Users, MapPin, ExternalLink, 
  Clock, Zap, ChevronRight, AlertTriangle,
  CheckCircle
} from 'lucide-react';

const IncidentIntelligenceCard = ({ event, onClose }) => {
  if (!event) return null;

  const isVerified = (event.verification_count || 1) > 1;
  const relevance = event.strategic_relevance || 'LOW';
  const relevanceColors = { CRITICAL: 'var(--accent-red)', HIGH: 'var(--accent-amber)', MEDIUM: 'var(--accent-cyan)', LOW: 'var(--text-dim)' };

  // Safe URL parsing
  const getSourceUrls = () => {
    const urls = event.source_urls?.length ? event.source_urls : [event.source_url];
    return urls.filter(u => u && u.startsWith('http'));
  };

  const safeDomain = (url) => {
    try { return new URL(url).hostname.replace('www.', ''); }
    catch { return 'source'; }
  };

  return (
    <div className="incident-intel-card glass-panel shadow-tactical animate-fade-in" style={{
      position: 'absolute',
      top: '20px',
      left: '20px',
      width: '420px',
      maxHeight: 'calc(100vh - 120px)',
      background: 'rgba(5, 7, 12, 0.97)',
      borderRadius: '12px',
      border: `1px solid ${isVerified ? 'rgba(16, 185, 129, 0.3)' : 'var(--border-glass)'}`,
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      color: 'var(--text-primary)',
      overflowY: 'auto'
    }}>
      {/* HEADER */}
      <div style={{
        padding: '15px 20px',
        background: isVerified ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255,255,255,0.03)',
        borderBottom: '1px solid var(--border-glass)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {isVerified ? (
            <CheckCircle size={14} color="var(--accent-green)" />
          ) : (
            <ShieldAlert size={14} color="var(--accent-red)" />
          )}
          <span style={{ fontSize: '10px', fontWeight: 900, letterSpacing: '2px', color: isVerified ? 'var(--accent-green)' : 'var(--text-dim)' }}>
            {isVerified ? `VERIFIED × ${event.verification_count} SOURCES` : `INTEL CASE: ${event.event_id?.slice(0, 8)}`}
          </span>
          <div style={{ 
            background: `${relevanceColors[relevance]}20`, 
            color: relevanceColors[relevance], 
            padding: '2px 6px', borderRadius: '4px', fontSize: '8px', fontWeight: 900,
            border: `1px solid ${relevanceColors[relevance]}40`
          }}>
            {relevance}
          </div>
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
        <h2 style={{ fontSize: '16px', fontWeight: 900, margin: '0 0 12px 0', lineHeight: '1.35' }}>
          {event.title}
        </h2>
        
        {/* META ROW */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <MapPin size={12} /> {event.location_raw || event.city || 'Sector'}, {event.country}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <Clock size={12} /> {event.event_time ? new Date(event.event_time).toLocaleString() : 'Unknown'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <Zap size={12} /> {event.event_type || 'Unknown'}
          </div>
        </div>

        {/* ENTITY GRID */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '20px' }}>
          <DetailBox label="PRIMARY ACTOR" value={event.actor1 || 'UNKNOWN'} icon={<Users size={14}/>} />
          <DetailBox label="SECONDARY ACTOR" value={event.actor2 || 'N/A'} icon={<Target size={14}/>} />
          <DetailBox label="FATALITIES" value={event.fatalities || 0} color="var(--accent-red)" icon={<AlertTriangle size={14}/>} />
          <DetailBox label="WEAPON SYSTEM" value={event.weapon || 'NOT SPECIFIED'} icon={<Zap size={14}/>} />
          <DetailBox label="GEO ACCURACY" value={`${Math.round((event.geo_confidence || 0) * 100)}%`} color="var(--accent-cyan)" />
          <DetailBox label="PRECISION" value={event.geo_precision === 1 ? 'EXACT' : event.geo_precision === 2 ? 'ADMIN' : 'BROAD'} color={event.geo_precision === 1 ? 'var(--accent-green)' : 'var(--accent-amber)'} />
        </div>
        
        {/* TACTICAL NOTES */}
        {event.notes && (
          <div style={{ padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', border: '1px solid var(--border-glass)', marginBottom: '20px' }}>
            <div style={{ fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)', letterSpacing: '1px', marginBottom: '6px' }}>TACTICAL NOTES</div>
            <div style={{ fontSize: '12px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
              {event.notes}
            </div>
          </div>
        )}

        {/* EVIDENCE TRAIN */}
        {getSourceUrls().length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', padding: '12px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
            <div style={{ fontSize: '8px', fontWeight: 900, color: isVerified ? 'var(--accent-green)' : 'var(--text-dim)', letterSpacing: '1px' }}>
              {isVerified ? '✓ MULTI-SOURCE VERIFIED' : 'SOURCE'}
            </div>
            {getSourceUrls().map((url, idx) => (
              <a 
                key={idx}
                href={url} target="_blank" rel="noreferrer"
                style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', color: 'var(--accent-cyan)', textDecoration: 'none', opacity: 0.85 }}
              >
                <ExternalLink size={10} /> SOURCE {idx + 1}: {safeDomain(url)}
              </a>
            ))}
          </div>
        )}
      </div>

      {/* FOOTER */}
      <div style={{ 
        padding: '12px 20px', background: 'rgba(0,0,0,0.3)', borderTop: '1px solid var(--border-glass)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      }}>
         <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: event.ai_classified !== false ? 'var(--accent-green)' : 'var(--accent-amber)' }}></div>
            <span style={{ fontSize: '9px', fontWeight: 900, color: 'var(--text-dim)' }}>
              {event.ai_classified !== false ? 'AI CLASSIFIED' : 'REGEX FALLBACK'}
            </span>
         </div>
         <div style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
           {event.source || 'SRC'} // {event.event_id?.slice(0, 12)}
         </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade-in { animation: fade-in 0.3s ease-out; }
      `}} />
    </div>
  );
};

const DetailBox = ({ label, value, color, icon }) => (
  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
    <div style={{ fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)', letterSpacing: '1px', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
      {icon} {label}
    </div>
    <div style={{ fontSize: '12px', fontWeight: 900, color: color || 'white', textTransform: 'uppercase', wordBreak: 'break-word' }}>
      {value ?? 'N/A'}
    </div>
  </div>
);

export default IncidentIntelligenceCard;
