import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Search, Sliders, Target, Shield, Flame, Activity, X, Info, Filter, MoreVertical, Zap } from 'lucide-react';

const LayerManager = ({ layers, updateLayer, onClose }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedGroups, setExpandedGroups] = useState({ tactical: true, strategic: true, surveillance: true });

  const toggleGroup = (group) => setExpandedGroups(prev => ({ ...prev, [group]: !prev[group] }));

  const filteredLayers = Object.entries(layers).filter(([_, v]) => 
    v.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groupConfigs = {
    tactical: { color: 'var(--accent-red)', title: 'LIVE TACTICAL' },
    strategic: { color: 'var(--accent-amber)', title: 'GEO-STRATEGIC' },
    surveillance: { color: 'var(--accent-cyan)', title: 'RECONNAISSANCE' }
  };

  return (
    <div className="layer-hub glass-panel" style={{ 
      position: 'fixed', top: '85px', left: '20px', width: '340px', zIndex: 2000,
      borderRadius: '12px', border: '1px solid var(--border-glass)', 
      animation: 'slide-in-left 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      maxHeight: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column',
      boxShadow: '0 25px 60px rgba(0,0,0,0.8)'
    }}>
      {/* HEADER */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '10px', height: '10px', background: 'var(--accent-green)', borderRadius: '50%', boxShadow: '0 0 10px var(--accent-green)', animation: 'pulse-glitch 2s infinite' }}></div>
          <span style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '2px', color: 'var(--text-primary)' }}>INTELLIGENCE MANAGER</span>
        </div>
        <button onClick={onClose} className="nav-command-btn" style={{ padding: '4px', background: 'transparent' }}>
          <X size={16} />
        </button>
      </div>

      {/* SEARCH INSTRUMENT */}
      <div style={{ padding: '15px 20px', borderBottom: '1px solid var(--border-glass)' }}>
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', opacity: 0.3 }} />
          <input 
            type="text" 
            className="layer-search-input" 
            style={{ 
                paddingLeft: '35px', width: '100%', 
                background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-glass)',
                borderRadius: '6px', fontSize: '11px', fontWeight: 600, color: 'white',
                height: '34px'
            }}
            placeholder="FILTER CHANNELS..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* ACCORDION LIST */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0' }} className="custom-scroller">
        {Object.entries(groupConfigs).map(([groupId, config]) => {
          const groupLayers = filteredLayers.filter(([_, l]) => l.group === groupId);
          if (groupLayers.length === 0) return null;

          return (
            <div key={groupId} style={{ marginBottom: '8px' }}>
              <div 
                className="layer-group-header" 
                onClick={() => toggleGroup(groupId)}
                style={{ 
                    padding: '8px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
                    cursor: 'pointer', background: 'rgba(255,255,255,0.01)',
                    borderBottom: '1px solid rgba(255,255,255,0.02)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {expandedGroups[groupId] ? <ChevronDown size={14} color={config.color} /> : <ChevronRight size={14} />}
                  <span style={{ fontSize: '10px', fontWeight: 900, letterSpacing: '1px', color: expandedGroups[groupId] ? config.color : 'var(--text-dim)' }}>
                    {config.title}
                  </span>
                </div>
                <div className="telemetry-badge" style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-dim)' }}>
                   [{groupLayers.filter(([_, l]) => l.active).length} / {groupLayers.length}]
                </div>
              </div>
              
              {expandedGroups[groupId] && (
                <div style={{ padding: '4px 0' }}>
                  {groupLayers.map(([key, layer]) => (
                    <div key={key} style={{ transition: 'all 0.2s' }}>
                      <div 
                        className="layer-item-surgical"
                        onClick={() => updateLayer(key, { active: !layer.active })}
                        style={{ 
                            padding: '10px 20px 10px 45px', display: 'flex', alignItems: 'center', gap: '15px', 
                            cursor: 'pointer', position: 'relative',
                            background: layer.active ? 'rgba(255,255,255,0.02)' : 'transparent'
                        }}
                      >
                         <div style={{ 
                             position: 'absolute', left: '20px', top: '50%', transform: 'translateY(-50%)',
                             width: '12px', height: '12px', borderRadius: '2px', border: '1px solid var(--border-glass)',
                             background: layer.active ? config.color : 'transparent',
                             boxShadow: layer.active ? `0 0 10px ${config.color}44` : 'none',
                             transition: 'all 0.2s'
                         }}></div>

                         <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                            {React.cloneElement(layer.icon, { size: 14, color: layer.active ? 'white' : 'var(--text-dim)' })}
                            <span style={{ fontSize: '11px', fontWeight: 700, color: layer.active ? 'white' : 'var(--text-secondary)' }}>
                                {layer.name.toUpperCase()}
                            </span>
                         </div>

                         {layer.active && (
                            <div className="active-data-pulse" style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'var(--accent-green)', boxShadow: '0 0 8px var(--accent-green)' }}></div>
                         )}
                         <div style={{ fontSize: '9px', fontWeight: 800, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            {layer.count}
                         </div>
                      </div>

                      {layer.active && (
                        <div style={{ padding: '0 20px 15px 45px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: 'var(--text-dim)', fontWeight: 800, marginBottom: '6px', letterSpacing: '0.5px' }}>
                            <span>SIGNAL INTENSITY</span>
                            <span>{Math.round(layer.opacity * 100)}%</span>
                          </div>
                          <input 
                            type="range" 
                            className="layer-opacity-slider" 
                            style={{ 
                                appearance: 'none', width: '100%', height: '2px', background: 'var(--border-glass)',
                                outline: 'none'
                             }}
                            min="0" max="1" step="0.05"
                            value={layer.opacity}
                            onChange={(e) => updateLayer(key, { opacity: parseFloat(e.target.value) })}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes slide-in-left { from { transform: translateX(-30px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes pulse-glitch { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(0.9); } }
        .layer-item-surgical:hover { background: rgba(255,255,255,0.04) !important; }
        .active-data-pulse { animation: blink 1.5s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
      `}} />
    </div>
  );
};

export default LayerManager;
