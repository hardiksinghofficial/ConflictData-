import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Cpu, ShieldCheck, Zap, Activity, Wifi, ShieldOff, Lock, Unlock } from 'lucide-react';

const AIAnalyst = ({ report, isAnalyzing, provider = "MULTI-ENGINE" }) => {
  const [statusText, setStatusText] = useState("AWAITING INTEL...");
  const [confidence, setConfidence] = useState(0);
  const scrollRef = useRef(null);

  // Auto-scroll logic
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [report]);

  // Dynamic status updates based on analysis state
  useEffect(() => {
    if (isAnalyzing) {
      const statuses = ["DECRYPTING FEEDS...", "ANALYZING SATELLITE DATA...", "CALCULATING ESCALATION...", "SENTIMENT SCRIBING...", "THREAT MAPPING..."];
      let i = 0;
      const timer = setInterval(() => {
        setStatusText(statuses[i]);
        setConfidence(prev => Math.min(98, prev + Math.random() * 5));
        i = (i + 1) % statuses.length;
      }, 3000);
      setStatusText("ESTABLISHING ENCRYPTED LINK...");
      setConfidence(45);
      return () => clearInterval(timer);
    } else {
      setStatusText(report ? "ANALYSIS COMPLETE" : "STANDBY");
      setConfidence(report ? 96.4 : 0);
    }
  }, [isAnalyzing, report]);

  return (
    <div className="ai-analyst-terminal glass-panel shadow-tactical" style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: 'rgba(5, 5, 8, 0.7)',
      borderRadius: '12px',
      overflow: 'hidden',
      border: '1px solid var(--border-glass)',
      position: 'relative'
    }}>
      {/* TERMINAL HEADER */}
      <div style={{
        padding: '12px 20px',
        background: 'rgba(0,0,0,0.5)',
        borderBottom: '1px solid var(--border-glass)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Terminal size={14} color="var(--accent-cyan)" />
          <span style={{ fontSize: '10px', fontWeight: 900, letterSpacing: '2px', color: 'var(--accent-cyan)' }}>
            TACTICAL AI ANALYST // VER: 4.8.2
          </span>
        </div>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: isAnalyzing ? 'var(--accent-red)' : 'var(--accent-green)', animation: isAnalyzing ? 'pulse-red 1s infinite' : 'none' }}></div>
            <span style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-dim)' }}>{isAnalyzing ? 'ACTIVE' : 'READY'}</span>
          </div>
          <div style={{ fontSize: '9px', fontWeight: 800, background: 'rgba(6, 182, 212, 0.1)', padding: '2px 8px', borderRadius: '4px', color: 'var(--accent-cyan)' }}>
            ENGINE: {provider}
          </div>
        </div>
      </div>

      {/* METRICS BAR */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        padding: '15px 20px',
        gap: '20px',
        borderBottom: '1px solid var(--border-glass)',
        background: 'rgba(0,0,0,0.2)'
      }}>
        <MetricItem label="ANALYSIS STATUS" value={statusText} color={isAnalyzing ? 'var(--accent-amber)' : 'var(--text-primary)'} />
        <MetricItem label="CONFIDENCE SCORE" value={`${confidence.toFixed(1)}%`} color="var(--accent-cyan)" />
        <MetricItem label="DATA SOURCE" value="HYBRID GDELT/LLAMA-3" />
      </div>

      {/* TERMINAL CONTENT */}
      <div 
        ref={scrollRef}
        className="terminal-scroll"
        style={{
          flex: 1,
          padding: '25px',
          overflowY: 'auto',
          fontFamily: 'var(--font-mono)',
          fontSize: '15px',
          lineHeight: '1.8',
          color: '#cbd5e1',
          whiteSpace: 'pre-wrap'
        }}
      >
        {!report && !isAnalyzing ? (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.3 }}>
             <Cpu size={48} style={{ marginBottom: '20px' }} />
             <div style={{ fontSize: '12px', fontWeight: 800, letterSpacing: '2px' }}>AWAITING TACTICAL CONTEXT</div>
             <div style={{ fontSize: '10px', marginTop: '10px' }}>SELECT A SECTOR ON THE MAP FOR DEEP ANALYSIS</div>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '25px', color: 'var(--accent-cyan)' }}>
               <Unlock size={14} />
               <span style={{ fontSize: '11px', fontWeight: 900 }}>[ENCRYPTED SITREP DECODED]</span>
            </div>
            {report}
            {isAnalyzing && <span className="cursor-blink">_</span>}
          </>
        )}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .cursor-blink { animation: blink 1s infinite; color: var(--accent-cyan); font-weight: bold; }
        @keyframes blink { 0%, 100% { opacity: 0; } 50% { opacity: 1; } }
        .terminal-scroll::-webkit-scrollbar { width: 4px; }
        .terminal-scroll::-webkit-scrollbar-thumb { background: var(--border-glass); border-radius: 4px; }
        @keyframes pulse-red { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
      `}} />
    </div>
  );
};

const MetricItem = ({ label, value, color }) => (
  <div>
    <div style={{ fontSize: '8px', fontWeight: 900, color: 'var(--text-dim)', letterSpacing: '1px', marginBottom: '4px' }}>{label}</div>
    <div style={{ fontSize: '11px', fontWeight: 800, color: color || 'var(--text-primary)', textTransform: 'uppercase' }}>{value}</div>
  </div>
);

export default AIAnalyst;
