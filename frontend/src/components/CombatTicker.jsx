import React, { useState, useEffect } from 'react';

const CombatTicker = () => {
  const [news, setNews] = useState([]);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const res = await fetch('https://hardik1231312-conflictdata.hf.space/api/v1/conflicts/ongoing?limit=20');
        const data = await res.json();
        setNews(data.data || []);
      } catch (err) {
        console.error("Ticker Error:", err);
      }
    };
    fetchNews();
    const interval = setInterval(fetchNews, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', background: 'rgba(244, 63, 94, 0.05)' }}>
      <div style={{ 
        position: 'absolute', 
        left: 0, 
        top: 0, 
        bottom: 0, 
        background: 'var(--accent-red)', 
        color: 'white', 
        display: 'flex', 
        alignItems: 'center', 
        padding: '0 15px', 
        zIndex: 10,
        fontSize: '12px',
        fontWeight: 800,
        letterSpacing: '1px'
      }}>
        TACTICAL FEED
      </div>
      
      <div className="ticker-wrapper" style={{ flex: 1, overflow: 'hidden', whiteSpace: 'nowrap' }}>
        <div className="ticker-content" style={{ display: 'inline-block', paddingLeft: '100%', animation: 'ticker 60s linear infinite' }}>
          {news.map((item, idx) => (
            <span key={item.event_id || idx} style={{ marginRight: '50px', fontSize: '12px', fontWeight: 600 }}>
              <span style={{ color: 'var(--accent-red)', marginRight: '8px' }}>[{item.event_type?.toUpperCase()}]</span>
              {item.title} — {item.city}, {item.country_iso3}
            </span>
          ))}
          {/* Duplicate for seamless loop */}
          {news.map((item, idx) => (
            <span key={`dup-${idx}`} style={{ marginRight: '50px', fontSize: '12px', fontWeight: 600 }}>
              <span style={{ color: 'var(--accent-red)', marginRight: '8px' }}>[{item.event_type?.toUpperCase()}]</span>
              {item.title} — {item.city}, {item.country_iso3}
            </span>
          ))}
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes ticker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-100%); }
        }
        .ticker-wrapper:hover .ticker-content {
          animation-play-state: paused;
        }
      `}} />
    </div>
  );
};

export default CombatTicker;
