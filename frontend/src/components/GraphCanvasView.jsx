import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  Search,
  Sliders,
  Layers,
  X,
  GitBranch,
  FileCheck,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api';
import { CopyHash, RiskGauge, StatusBadge } from './shared';

export default function GraphCanvasView({
  initialCenterId = null,
  onLaunchTrace,
  onLaunchInvestigate,
}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  const [centerId, setCenterId] = useState(initialCenterId || '');
  const [hops, setHops] = useState(2);
  const [layoutName, setLayoutName] = useState('cose');
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [entitiesList, setEntitiesList] = useState([]);

  // Load available entities for quick selection
  useEffect(() => {
    api.getEntities(50).then((ents) => {
      if (ents && ents.length > 0) {
        setEntitiesList(ents);
        if (!centerId) {
          setCenterId(ents[0].entity_id);
        }
      }
    }).catch(console.error);
  }, []);

  // Fetch subgraph and render in Cytoscape
  const loadGraph = async (targetId, hopCount = hops) => {
    if (!targetId || !containerRef.current) return;
    setLoading(true);
    setSelectedNode(null);

    try {
      const data = await api.getEgoSubgraph(targetId, hopCount);
      const elements = [];

      // Add nodes
      (data.nodes || []).forEach((n) => {
        const risk = n.risk_score ?? n.risk ?? null;
        let color = '#38bdf8'; // default cyan
        if (n.type === 'IP') color = '#a855f7';
        else if (n.type === 'Transaction') color = '#64748b';
        else if (n.type === 'Address') color = '#0284c7';
        else if (risk !== null && (risk >= 0.7 || ['DARKNET', 'RANSOMWARE', 'MIXER'].includes(n.entity_type))) color = '#f43f5e';
        else if (risk !== null && risk >= 0.4) color = '#fbbf24';
        else if (n.type === 'Entity') color = '#00f0ff';

        elements.push({
          group: 'nodes',
          data: {
            id: n.id,
            label: n.label || n.id.substring(0, 10),
            type: n.type,
            entity_type: n.entity_type || 'INDIVIDUAL',
            risk: risk,
            bgColor: color,
            isCenter: n.id === targetId,
          },
        });
      });

      // Add edges
      (data.edges || []).forEach((e, idx) => {
        elements.push({
          group: 'edges',
          data: {
            id: e.id || `e_${idx}`,
            source: e.source,
            target: e.target,
            label: e.edge_type || '',
            weight: typeof e.weight === 'number' ? e.weight : null,
          },
        });
      });

      // Initialize or update Cytoscape instance
      if (cyRef.current) {
        cyRef.current.destroy();
      }

      const cy = cytoscape({
        container: containerRef.current,
        elements: elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(bgColor)',
              'label': 'data(label)',
              'color': '#ffffff',
              'font-size': '10px',
              'font-family': 'monospace',
              'text-valign': 'bottom',
              'text-margin-y': 4,
              'width': 26,
              'height': 26,
              'border-width': 2,
              'border-color': 'rgba(255, 255, 255, 0.4)',
              'transition-property': 'background-color, line-color, target-arrow-color, width, height',
              'transition-duration': '0.2s',
            },
          },
          {
            selector: 'node[?isCenter]',
            style: {
              'width': 40,
              'height': 40,
              'border-width': 3,
              'border-color': '#00f2fe',
              'box-shadow': '0 0 16px rgba(0, 242, 254, 0.6)',
            },
          },
          {
            selector: 'node[entity_type = "EXCHANGE"]',
            style: {
              'shape': 'hexagon',
              'width': 32,
              'height': 32,
              'background-color': '#10b981',
              'border-color': 'rgba(16, 185, 129, 0.6)',
            },
          },
          {
            selector: 'node[entity_type = "MIXER"], node[entity_type = "DARKNET"]',
            style: {
              'shape': 'diamond',
              'width': 30,
              'height': 30,
              'background-color': '#ef4444',
              'border-color': 'rgba(239, 68, 68, 0.6)',
            },
          },
          {
            selector: 'node[type = "IP"]',
            style: {
              'shape': 'octagon',
              'width': 26,
              'height': 26,
              'background-color': '#8b5cf6',
            },
          },
          {
            selector: 'node[type = "Transaction"]',
            style: {
              'shape': 'round-rectangle',
              'width': 26,
              'height': 16,
              'background-color': '#475569',
              'border-color': 'rgba(255, 255, 255, 0.25)',
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 1.6,
              'line-color': 'rgba(255, 255, 255, 0.18)',
              'target-arrow-color': 'rgba(255, 255, 255, 0.35)',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'arrow-scale': 0.85,
            },
          },
          {
            selector: 'edge[weight > 0.4], edge[label = "taint"], edge[label = "SPEND"]',
            style: {
              'line-color': '#f7931a',
              'target-arrow-color': '#f7931a',
              'line-style': 'dashed',
              'line-dash-pattern': [6, 3],
              'width': 2.2,
            },
          },
          {
            selector: 'node:selected',
            style: {
              'border-width': 3,
              'border-color': '#ffffff',
              'box-shadow': '0 0 20px #ffffff',
            },
          },
        ],
        layout: {
          name: layoutName,
          animate: true,
          padding: 30,
        },
      });

      cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        setSelectedNode(node.data());
      });

      cy.on('tap', (evt) => {
        if (evt.target === cy) {
          setSelectedNode(null);
        }
      });

      cyRef.current = cy;
    } catch (err) {
      console.error('Failed to load subgraph:', err);
    } finally {
      setLoading(false);
    }
  };

  // Reload when centerId changes
  useEffect(() => {
    if (centerId) {
      loadGraph(centerId, hops);
    }
  }, [centerId, hops, layoutName]);

  const handleZoom = (factor) => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * factor);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(30);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Control Bar */}
      <div
        className="card"
        style={{
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: '320px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={16}
              style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }}
            />
            <input
              type="text"
              className="input mono"
              style={{ width: '100%', paddingLeft: '2.25rem' }}
              placeholder="Enter Entity ID, Address, or IP..."
              value={centerId}
              onChange={(e) => setCenterId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadGraph(centerId, hops)}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={() => loadGraph(centerId, hops)}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Rendering...' : 'Expand Graph'}
          </button>
        </div>

        {/* Layout & Hop Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            <Layers size={15} />
            <span>Layout:</span>
            <select
              className="select"
              value={layoutName}
              onChange={(e) => setLayoutName(e.target.value)}
            >
              <option value="cose">Force-Directed (Cose)</option>
              <option value="concentric">Concentric Circles</option>
              <option value="circle">Circular Topology</option>
              <option value="grid">Orthogonal Grid</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            <Sliders size={15} />
            <span>Horizon:</span>
            <select
              className="select"
              value={hops}
              onChange={(e) => setHops(parseInt(e.target.value))}
            >
              <option value={1}>1 Hop (Direct Neighbors)</option>
              <option value={2}>2 Hops (Intermediaries)</option>
              <option value={3}>3 Hops (Deep Horizon)</option>
            </select>
          </div>

          {/* Quick Entities Dropdown */}
          {entitiesList.length > 0 && (
            <select
              className="select"
              style={{ maxWidth: '170px' }}
              onChange={(e) => {
                setCenterId(e.target.value);
                loadGraph(e.target.value, hops);
              }}
              value={centerId}
            >
              <option value="" disabled>Select Entity...</option>
              {entitiesList.map((ent) => (
                <option key={ent.entity_id} value={ent.entity_id}>
                  {ent.entity_id} ({ent.entity_type})
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Viewport Canvas with Floating Overlays */}
      <div className="graph-viewport-container" style={{ position: 'relative', height: '620px', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        {/* Viewport Action Controls */}
        <div className="graph-controls-overlay" style={{ position: 'absolute', top: '12px', right: '12px', zIndex: 10, display: 'flex', gap: '6px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => handleZoom(1.25)} title="Zoom In">
            <ZoomIn size={14} />
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => handleZoom(0.8)} title="Zoom Out">
            <ZoomOut size={14} />
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handleFit} title="Fit to Viewport">
            <Maximize2 size={14} />
          </button>
        </div>

        {/* Legend Overlay */}
        <div
          className="graph-legend-overlay"
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            zIndex: 10,
            background: 'rgba(11, 17, 32, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            padding: '8px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            fontSize: '0.72rem',
          }}
        >
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="legend-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00f2fe', boxShadow: '0 0 6px #00f2fe' }}></span>
            <span>Target Entity</span>
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', background: '#10b981', display: 'inline-block', clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }}></span>
            <span>Exchange</span>
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', background: '#ef4444', transform: 'rotate(45deg)', display: 'inline-block' }}></span>
            <span>Mixer / Illicit</span>
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '14px', height: '0px', borderTop: '2px dashed #f7931a', display: 'inline-block' }}></span>
            <span style={{ color: 'var(--btc-orange)' }}>Tainted Satoshi Flow</span>
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="legend-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#8b5cf6' }}></span>
            <span>Broadcast IP</span>
          </div>
          <div className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '10px', height: '6px', borderRadius: '2px', background: '#475569', display: 'inline-block' }}></span>
            <span>Transaction</span>
          </div>
        </div>

        {/* Cytoscape DOM container */}
        <div id="cy-canvas" ref={containerRef} style={{ width: '100%', height: '100%', backgroundColor: '#060911' }}></div>
      </div>

      {/* Slide-Over Inspection Drawer */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            className="drawer-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setSelectedNode(null)}
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(6, 9, 17, 0.65)',
              backdropFilter: 'blur(4px)',
              zIndex: 999,
              display: 'flex',
              justifyContent: 'flex-end',
            }}
          >
            <motion.div
              className="drawer-panel"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 400, damping: 35 }}
              onClick={(e) => e.stopPropagation()}
              style={{
                width: '100%',
                maxWidth: '420px',
                height: '100%',
                backgroundColor: '#0b1120',
                borderLeft: '1px solid rgba(0, 240, 255, 0.25)',
                boxShadow: '-10px 0 30px rgba(0, 0, 0, 0.6)',
                padding: '1.5rem',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ShieldAlert size={18} style={{ color: selectedNode.risk > 0.6 ? 'var(--crimson)' : 'var(--btc-orange)' }} />
                    <h3 style={{ fontSize: '1.15rem', color: '#fff', fontWeight: 700 }}>
                      Node Inspector: {selectedNode.type}
                    </h3>
                  </div>
                  <div style={{ marginTop: '0.4rem' }}>
                    <CopyHash value={selectedNode.id} label="Node ID" truncate={false} />
                  </div>
                </div>

                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => setSelectedNode(null)}
                  style={{ padding: '0.35rem 0.5rem' }}
                >
                  <X size={16} />
                </button>
              </div>

              {/* Telemetry Details */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginBottom: '1.5rem' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>Classification:</span>
                    <StatusBadge status={selectedNode.entity_type} size="sm" />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>Risk Score:</span>
                    <RiskGauge score={selectedNode.risk ?? 0} variant="bar" size="sm" />
                  </div>
                </div>

                {/* Action Buttons for Selected Node */}
                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                  <button
                    className="btn btn-primary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => {
                      onLaunchTrace(selectedNode.id);
                      setSelectedNode(null);
                    }}
                  >
                    <GitBranch size={14} />
                    Trace Taint
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ flex: 1 }}
                    onClick={() => {
                      onLaunchInvestigate(selectedNode.id);
                      setSelectedNode(null);
                    }}
                  >
                    <FileCheck size={14} />
                    Investigate
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
