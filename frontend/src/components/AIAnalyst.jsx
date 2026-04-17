import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Cpu, RefreshCw } from 'lucide-react';

const AIAnalyst = () => {
  const [report, setReport] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const scrollRef = useRef(null);

  const startAnalysis = () => {
    setReport("");
    setIsAnalyzing(true);
    
    // Using native Fetch with ReadableStream for better cross-origin SSE handling
    const fetchAI = async () => {
      try {
        const response = await fetch('https://hardik1231312-conflictdata.hf.space/api/v1/ai/analyze');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          // Parse potential SSE data prefix
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
               const content = line.replace('data: ', '');
               setReport(prev => prev + content);
            }
          }
        }
      } catch (err) {
        setReport(prev => prev + "\n\n[ERROR: INTELLIGENCE LINK SEVERED]");
        console.error("AI Stream Error:", err);
      } finally {
        setIsAnalyzing(false);
      }
    };

    fetchAI();
  };

  useEffect(() => {
    startAnalysis();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [report]);

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '15px', borderBottom: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Cpu size={18} color="var(--accent-green)" />
          <span style={{ fontWeight: 700, fontSize: '13px', letterSpacing: '1px' }}>VIRTUAL ANALYST</span>
        </div>
        <button 
          onClick={startAnalysis} 
          disabled={isAnalyzing}
          style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
        >
          <RefreshCw size={16} className={isAnalyzing ? 'spin' : ''} />
        </button>
      </div>

      <div 
        ref={scrollRef}
        style={{ 
          flex: 1, 
          padding: '20px', 
          fontFamily: 'var(--font-mono)', 
          fontSize: '13px', 
          lineHeight: '1.6', 
          overflowY: 'auto',
          color: '#d1d5db',
          whiteSpace: 'pre-wrap'
        }}
      >
        {report || (isAnalyzing ? "INITIALIZING ANALYTIC SEQUENCE..." : "PENDING DATA...")}
        {isAnalyzing && <span className="cursor-blink">|</span>}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .spin { animation: spin 2s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .cursor-blink { animation: blink 1s infinite; color: var(--accent-green); font-weight: bold; }
        @keyframes blink { 0%, 100% { opacity: 0; } 50% { opacity: 1; } }
      `}} />
    </div>
  );
};

export default AIAnalyst;
