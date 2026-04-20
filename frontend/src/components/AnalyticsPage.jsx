import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  ArrowLeft, ShieldCheck, Zap, Globe, Clock, Box, TrendingUp, Users, 
  AlertTriangle, Target, Activity, Radar, BarChart3, Database
} from 'lucide-react';
import AIAnalyst from './AIAnalyst';
import API_BASE from '../config';

const AnalyticsPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [report, setReport] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [zuluTime, setZuluTime] = useState(new Date().toUTCString());
  const [sitrep, setSitrep] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [theaters, setTheaters] = useState([]);
  const [pulse, setPulse] = useState(false);

  // ZULU Clock
  useEffect(() => {
    const timer = setInterval(() => setZuluTime(new Date().toUTCString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch strategic intel data
  useEffect(() => {
    const fetchIntel = async () => {
      try {
        const [srRes, fcRes, thRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/intel/sitrep`),
          fetch(`${API_BASE}/api/v1/intel/forecast`),
          fetch(`${API_BASE}/api/v1/intel/theaters`)
        ]);
        setSitrep(await srRes.json());
        setForecast(await fcRes.json());
        setTheaters(await thRes.json());
      } catch (err) {
        console.error("Failed to fetch strategic intel:", err);
      }
    };
    fetchIntel();
    const interval = setInterval(fetchIntel, 60000); // 1-minute refresh
    return () => clearInterval(interval);
  }, []);

  const startAnalysis = (targetContext = null) => {
    setReport("");
    setIsAnalyzing(true);
    setPulse(true);
    
    const fetchAI = async () => {
      try {
        const url = targetContext 
          ? `${API_BASE}/api/v1/ai/analyze?context=${encodeURIComponent(targetContext)}`
          : `${API_BASE}/api/v1/ai/analyze`;

        const response = await fetch(url);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
               const content = line.replace('data: ', '');
               setReport(prev => prev + content);
            }
          }
        }
      } catch (err) {
        setReport(prev => prev + "\n\n[CRITICAL ERROR: INTELLIGENCE LINK SEVERED]");
      } finally {
        setIsAnalyzing(false);
        setPulse(false);
      }
    };

    fetchAI();
  };

  useEffect(() => {
    // Check if we came here from a specific context (like 'Analyze Sector')
    const context = location.state?.context || null;
    startAnalysis(context);
    // eslint-disable-next-line
  }, [location.state]);

  return (
    <div className="analytics-command-hub" style={{ 
      height: '100vh', 
      width: '100vw', 
      background: 'var(--bg-obsidian)',
      display: 'flex',
      flexDirection: 'column',
      color: 'var(--text-primary)',
      overflow: 'hidden',
      position: 'relative'
    }}>
      <div className="scanline"></div>
      
      {/* PROFESSIONAL MISSION CONTROL HEADER */}
      <header className="glass-panel" style={{ 
        height: '70px', 
        display: 'flex', 
        alignItems: 'center', 
        padding: '0 30px', 
        justifyContent: 'space-between', 
        borderBottom: '1px solid var(--border-glass)',
        background: 'rgba(5, 5, 10, 0.95)',
        zIndex: 100
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '25px' }}>
          <button 
            onClick={() => navigate('/')}
            className="nav-command-btn"
            style={{ 
              height: '40px', 
              padding: '0 20px', 
              border: '1px solid var(--border-glass)',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '11px',
              fontWeight: 900,
              cursor: 'pointer'
            }}
          >
            <ArrowLeft size={16} /> RTB // BASE CMD
          </button>
          
          <div style={{ width: '1px', height: '24px', background: 'var(--border-glass)' }}></div>
          
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-red)', boxShadow: '0 0 10px var(--accent-red)' }}></div>
              <h1 style={{ fontSize: '16px', fontWeight: 900, letterSpacing: '4px', margin: 0 }}>STRATEGIC<span style={{ color: 'var(--accent-red)' }}>INTEL</span></h1>
            </div>
            <div style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-dim)', letterSpacing: '1px', marginLeft: '16px' }}>
              LEVEL-5 GLOBAL MONITORING // SOURCE: MULTI-ENGINE AI
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '50px', alignItems: 'center' }}>
          <CommandMetric label="SATELLITE LINK" value="ACTIVE" icon={<Zap size={14} color="var(--accent-cyan)" />} color="var(--accent-cyan)" />
          <CommandMetric label="THREAT INTENSITY" value={sitrep?.intensity || 'ANALYZING'} color={sitrep?.intensity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-amber)'} />
          <CommandMetric label="ZULU TIME" value={zuluTime.split(' ')[4]} icon={<Clock size={14} />} color="var(--accent-green)" />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '15px', background: 'rgba(6, 182, 212, 0.05)', padding: '8px 15px', borderRadius: '8px', border: '1px solid rgba(6, 182, 212, 0.1)' }}>
          <ShieldCheck size={20} color="var(--accent-cyan)" />
          <div style={{ fontSize: '10px', fontWeight: 900, color: 'var(--accent-cyan)' }}>ENCRYPTED SESSION</div>
        </div>
      </header>

      {/* DASHBOARD GRID */}
      <main style={{ flex: 1, padding: '20px', display: 'grid', gridTemplateColumns: '400px 1fr 380px', gap: '20px', overflow: 'hidden' }}>
        
        {/* LEFT COLUMN: TACTICAL METRICS */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto', paddingRight: '10px' }}>
          
          {/* Situation Briefing */}
          <div className="glass-panel card-hover" style={{ padding: '20px', borderRadius: '12px', borderLeft: '4px solid var(--accent-cyan)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
              <Globe size={18} color="var(--accent-cyan)" />
              <span style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '1.5px' }}>SITUATION BRIEFING</span>
            </div>
            <p style={{ fontSize: '13px', lineHeight: '1.7', color: 'var(--text-secondary)', fontWeight: 500 }}>
              {sitrep?.summary || "Initializing deep scan of global conflict signatures..."}
            </p>
          </div>

          {/* Conflict Theaters Persistence */}
          <div className="glass-panel" style={{ flex: 1, padding: '20px', borderRadius: '12px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
              <Target size={18} color="var(--accent-red)" />
              <span style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '1.5px' }}>THEATERS OF CONCERN</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
              {theaters.map((t, idx) => (
                <div key={idx} className="theater-item" style={{ 
                  background: 'rgba(255,255,255,0.02)', 
                  padding: '15px', 
                  borderRadius: '10px', 
                  border: '1px solid var(--border-glass)',
                  transition: 'all 0.3s'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 900 }}>{t.name}</span>
                    <span style={{ fontSize: '10px', fontWeight: 900, color: t.stability_rating < 50 ? 'var(--accent-red)' : 'var(--accent-amber)' }}>{t.intensity}</span>
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginBottom: '10px' }}>{t.dominant_actor || 'NON-STATE ACTORS'} // STABILITY: {Math.round(t.stability_rating)}%</div>
                  <div style={{ width: '100%', height: '3px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                    <div style={{ width: `${t.stability_rating}%`, height: '100%', background: t.stability_rating < 50 ? 'var(--accent-red)' : 'var(--accent-cyan)', borderRadius: '2px' }}></div>
                  </div>
                </div>
              ))}
              {theaters.length === 0 && <div style={{ textAlign: 'center', padding: '40px', opacity: 0.2 }}><Radar size={32} style={{ margin: 'auto' }} /></div>}
            </div>
          </div>
        </section>

        {/* MIDDLE COLUMN: THE AI ANALYST MODULE */}
        <section style={{ display: 'flex', flexDirection: 'column' }}>
           <AIAnalyst report={report} isAnalyzing={isAnalyzing} provider="HYBRID-70B" />
        </section>

        {/* RIGHT COLUMN: STRATEGIC FORECAST & ANALYTICS */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* AI Forecast Card */}
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', background: 'rgba(244, 63, 94, 0.03)', border: '1px solid rgba(244, 63, 94, 0.1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
              <TrendingUp size={18} color="var(--accent-red)" />
              <span style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '1.5px', color: 'var(--accent-red)' }}>STRATEGIC FORECAST</span>
            </div>
            <p style={{ fontSize: '13px', lineHeight: '1.7', color: '#cbd5e1', fontStyle: 'italic' }}>
              "{forecast?.forecast || "Simulation in progress... evaluating escalation vectors."}"
            </p>
            <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ flex: 1, height: '1px', background: 'rgba(244,63,94,0.2)' }}></div>
              <span style={{ fontSize: '9px', fontWeight: 900, color: 'var(--accent-red)' }}>RISK: {forecast?.risk_level || 'UNKNOWN'}</span>
              <div style={{ flex: 1, height: '1px', background: 'rgba(244,63,94,0.2)' }}></div>
            </div>
          </div>

          {/* Impact Stats Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
             <AnalyticsMiniCard icon={<Activity size={16} />} label="ACTIVE OPS" value={theaters.length} />
             <AnalyticsMiniCard icon={<Users size={16} />} label="ACTORS" value={sitrep?.stats?.most_active_actor ? 1 : 0} />
             <AnalyticsMiniCard icon={<Database size={16} />} label="INTEL FEED" value={`${sitrep?.stats?.total_events || 0} ITEMS`} />
             <AnalyticsMiniCard icon={<BarChart3 size={16} />} label="FATALITIES" value={sitrep?.stats?.total_fatalities || 0} color="var(--accent-red)" />
          </div>

          {/* Strategic Narrative Block */}
          <div className="glass-panel" style={{ flex: 1, padding: '25px', borderRadius: '12px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-glass)' }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                <Box size={18} color="var(--accent-amber)" />
                <span style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '1.5px' }}>COMMAND DIRECTIVE</span>
             </div>
             <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.8' }}>
                Personnel should monitor the <span style={{ color: 'var(--accent-cyan)' }}>Tactical Map</span> for kinetic signatures. Analysis Engine currently prioritizing high-severity surges in <span style={{ color: 'var(--accent-red)' }}>{sitrep?.stats?.top_country || 'global theaters'}</span>. 
                <br /><br />
                All data is sourced from real-time GDELT and satellite news clustering. Multi-engine failover is active.
             </div>
          </div>
        </section>
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        .analytics-command-hub { background: radial-gradient(circle at 50% 100%, #101018 0%, #020203 100%); }
        .theater-item:hover { background: rgba(255,255,255,0.06) !important; transform: translateX(5px); }
        .card-hover:hover { border-color: var(--accent-cyan) !important; }
        .scanline { position: absolute; top:0; left:0; width:100%; height:100%; background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.05) 50%); background-size: 100% 4px; pointer-events: none; z-index: 5; opacity: 0.3; }
        @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
      `}} />
    </div>
  );
};

const CommandMetric = ({ label, value, icon, color }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
    <div style={{ textAlign: 'right' }}>
       <div style={{ fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)', letterSpacing: '1px' }}>{label}</div>
       <div style={{ fontSize: '12px', fontWeight: 900, color: color || 'var(--text-primary)' }}>{value}</div>
    </div>
    {icon}
  </div>
);

const AnalyticsMiniCard = ({ icon, label, value, color }) => (
  <div className="glass-panel" style={{ padding: '15px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '12px' }}>
     <div style={{ color: color || 'var(--accent-cyan)', opacity: 0.8 }}>{icon}</div>
     <div>
        <div style={{ fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)', letterSpacing: '1px' }}>{label}</div>
        <div style={{ fontSize: '13px', fontWeight: 900, color: 'white' }}>{value}</div>
     </div>
  </div>
);

export default AnalyticsPage;
