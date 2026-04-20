import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Terminal, Cpu, RefreshCw, ArrowLeft, ShieldCheck, Zap, Globe, Clock, Box, TrendingUp, Users, AlertTriangle } from 'lucide-react';
import API_BASE from '../config';

const AnalyticsPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [report, setReport] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [zuluTime, setZuluTime] = useState(new Date().toUTCString());
  const [sitrep, setSitrep] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [actors, setActors] = useState([]);
  const scrollRef = useRef(null);

  // ZULU Clock
  useEffect(() => {
    const timer = setInterval(() => setZuluTime(new Date().toUTCString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch structured intel data
  useEffect(() => {
    const fetchIntel = async () => {
      try {
        const [srRes, fcRes, acRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/intel/sitrep`),
          fetch(`${API_BASE}/api/v1/intel/forecast`),
          fetch(`${API_BASE}/api/v1/intel/actors`)
        ]);
        setSitrep(await srRes.json());
        setForecast(await fcRes.json());
        setActors(await acRes.json());
      } catch (err) {
        console.error("Failed to fetch strategic intel:", err);
      }
    };
    fetchIntel();
  }, []);

  const startAnalysis = (targetContext = null) => {
    setReport("");
    setIsAnalyzing(true);
    
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
      }
    };

    fetchAI();
  };

  useEffect(() => {
    // Check if we came here from a specific context (like 'Analyze Sector')
    const context = location.state?.context || null;
    startAnalysis(context);
  }, [location.state]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [report]);

  return (
    <div className="analytics-layout" style={{ 
      height: '100vh', 
      width: '100vw', 
      background: 'var(--bg-obsidian)',
      display: 'flex',
      flexDirection: 'column',
      color: 'var(--text-primary)',
      overflow: 'hidden'
    }}>
      {/* ANALYTICS HEADER */}
      <header className="glass-panel" style={{ height: '70px', display: 'flex', alignItems: 'center', padding: '0 30px', justifyContent: 'space-between', borderBottom: '1px solid var(--border-glass)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <button 
            onClick={() => navigate('/')}
            className="nav-command-btn"
            style={{ padding: '8px', border: '1px solid var(--border-glass)' }}
          >
            <ArrowLeft size={18} /> BACK TO COMMAND
          </button>
          <div style={{ width: '1px', height: '24px', background: 'var(--border-glass)' }}></div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 900, letterSpacing: '2px' }}>STRATEGIC COMMAND HUB</div>
            <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '1px' }}>SITREP // SOURCE: ConflictIQ Intelligence Layer // {zuluTime.split(' ')[4]} ZULU</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '25px', alignItems: 'center' }}>
          <div style={{ textAlign: 'right' }}>
             <div style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-dim)' }}>LINK STATUS</div>
             <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--accent-green)' }}>ENCRYPTED</div>
          </div>
          <ShieldCheck size={28} color="var(--accent-green)" />
        </div>
      </header>

      {/* MAIN CONTENT AREA */}
      <main style={{ flex: 1, padding: '20px', position: 'relative', overflow: 'hidden', display: 'flex', gap: '20px' }}>
        <div className="scanline" style={{ opacity: 0.1 }}></div>

        {/* LEFT PANEL: Tactical Intelligence */}
        <aside style={{ width: '350px', display: 'flex', flexDirection: 'column', gap: '15px', overflowY: 'auto', paddingRight: '5px' }}>
          
          {/* Daily Sitrep Card */}
          <section className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderLeft: '4px solid var(--accent-cyan)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <Globe size={18} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '12px', fontWeight: 900, letterSpacing: '1px' }}>DAILY SITREP</h3>
            </div>
            <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-dim)' }}>
              {sitrep?.summary || "Analyzing latest satellite and GDELT feeds..."}
            </p>
          </section>

          {/* Strategic Forecast Card */}
          <section className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderLeft: `4px solid ${forecast?.risk_level === 'CRITICAL' ? 'var(--accent-red)' : 'var(--accent-orange)'}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <AlertTriangle size={18} color={forecast?.risk_level === 'CRITICAL' ? 'var(--accent-red)' : 'var(--accent-orange)'} />
              <h3 style={{ fontSize: '12px', fontWeight: 900, letterSpacing: '1px' }}>STRATEGIC FORECAST</h3>
            </div>
            <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-dim)', fontStyle: 'italic' }}>
              {forecast?.forecast || "Calculating escalation probabilities..."}
            </p>
            {forecast?.risk_level === 'CRITICAL' && (
              <div style={{ marginTop: '10px', fontSize: '10px', fontWeight: 900, color: 'var(--accent-red)', letterSpacing: '1px' }}>
                [WARNING: MULTIPLE SURGE DETECTED]
              </div>
            )}
          </section>

          {/* Top Actors Persistence */}
          <section className="glass-panel" style={{ padding: '20px', borderRadius: '12px' }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
              <Users size={18} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '12px', fontWeight: 900, letterSpacing: '1px' }}>ACTOR PERSISTENCE (7D)</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {actors.slice(0, 5).map((actor, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px', background: 'rgba(255,255,255,0.03)', borderRadius: '4px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700 }}>{actor.actor1}</span>
                  <span style={{ fontSize: '11px', color: 'var(--accent-red)', fontWeight: 800 }}>{actor.involvement_count} OPS</span>
                </div>
              ))}
              {actors.length === 0 && <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Identifying key actors...</div>}
            </div>
          </section>
        </aside>

        {/* RIGHT PANEL: The Deep Analysis Readout */}
        <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column' }}>
          {/* Status Indicators */}
          <div style={{ display: 'flex', gap: '15px', marginBottom: '15px' }}>
             <div className="glass-panel" style={{ padding: '10px 20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Cpu size={14} color="var(--accent-cyan)" />
                <span style={{ fontSize: '9px', fontWeight: 900, letterSpacing: '1px' }}>ANALYSIS ENGINE ONLINE</span>
             </div>
             {isAnalyzing && (
               <div className="glass-panel" style={{ padding: '10px 20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px', borderColor: 'var(--accent-red)' }}>
                  <RefreshCw size={14} className="spin" color="var(--accent-red)" />
                  <span style={{ fontSize: '9px', fontWeight: 900, letterSpacing: '1px', color: 'var(--accent-red)' }}>INCOMING TACTICAL FEED</span>
               </div>
             )}
          </div>

          <div className="glass-panel shadow-tactical" style={{ 
            flex: 1,
            padding: '30px', 
            borderRadius: '12px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            background: 'rgba(0,0,0,0.4)'
          }}>
            <div 
              ref={scrollRef}
              style={{ 
                flex: 1,
                overflowY: 'auto',
                fontFamily: 'var(--font-mono)', 
                fontSize: '15px', 
                lineHeight: '1.8', 
                color: '#cbd5e1',
                whiteSpace: 'pre-wrap',
                paddingRight: '15px'
              }}
            >
              <div style={{ marginBottom: '20px', color: 'var(--accent-cyan)', fontWeight: 800, fontSize: '12px' }}>
                [INITIATING DEEP SECTOR ANALYSIS]
              </div>
              {report || "AWAITING BROADCAST..."}
              {isAnalyzing && <span className="cursor-blink">_</span>}
            </div>
          </div>
        </div>
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        .spin { animation: spin 2s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .cursor-blink { animation: blink 1s infinite; color: var(--accent-green); font-weight: bold; }
        @keyframes blink { 0%, 100% { opacity: 0; } 50% { opacity: 1; } }
        .analytics-layout { background: radial-gradient(circle at 50% 100%, #0c0c14 0%, #020203 100%); }
        .glass-panel::-webkit-scrollbar { width: 4px; }
        .glass-panel::-webkit-scrollbar-thumb { background: var(--border-glass); border-radius: 4px; }
      `}} />
    </div>
  );
};

export default AnalyticsPage;
