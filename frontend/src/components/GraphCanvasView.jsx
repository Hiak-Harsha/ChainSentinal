import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
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
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api';

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
  const [minRisk, setMinRisk] = useState(0.0);

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
        const risk = n.risk_score || n.risk || 0.0;
        let color = '#3b82f6'; // default blue
        if (n.type === 'IP') color = '#8b5cf6';
        else if (n.type === 'Transaction') color = '#64748b';
        else if (n.type === 'Address') color = '#0284c7';
        else if (risk >= 0.7 || ['DARKNET', 'RANSOMWARE', 'MIXER'].includes(n.entity_type)) color = '#ef4444';
        else if (risk >= 0.4) color = '#f59e0b';
        else if (n.type === 'Entity') color = '#00f2fe';

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
            weight: e.weight || 1.0,
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
              'width': 28,
              'height': 28,
              'border-width': 2,
              'border-color': 'rgba(255, 255, 255, 0.4)',
              'transition-property': 'background-color, line-color, target-arrow-color',
              'transition-duration': '0.2s',
            },
          },
          {
            selector: 'node[?isCenter]',
            style: {
              'width': 38,
              'height': 38,
              'border-width': 3,
              'border-color': '#00f2fe',
              'box-shadow': '0 0 15px rgba(0, 242, 254, 0.6)',
            },
          },
          {
            selector: 'node[type = "IP"]',
            style: {
              'shape': 'diamond',
              'width': 26,
              'height': 26,
            },
          },
          {
            selector: 'node[type = "Transaction"]',
            style: {
              'shape': 'rectangle',
              'width': 24,
              'height': 16,
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 1.5,
              'line-color': 'rgba(255, 255, 255, 0.18)',
              'target-arrow-color': 'rgba(255, 255, 255, 0.3)',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              'arrow-scale': 0.8,
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
    <div>
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
      <div className="graph-viewport-container">
        {/* Viewport Action Controls */}
        <div className="graph-controls-overlay">
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
        <div className="graph-legend-overlay">
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#00f2fe' }}></span>
            <span>Target Entity</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#ef4444' }}></span>
            <span>High Risk / Illicit</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#8b5cf6' }}></span>
            <span>Broadcast IP</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#0284c7' }}></span>
            <span>Address</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#64748b' }}></span>
            <span>Transaction</span>
          </div>
        </div>

        {/* Cytoscape DOM container */}
        <div id="cy-canvas" ref={containerRef}></div>
      </div>

      {/* Slide-Over Inspection Drawer */}
      {selectedNode && (
        <div className="drawer-backdrop" onClick={() => setSelectedNode(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ShieldAlert size={18} style={{ color: selectedNode.risk > 0.6 ? 'var(--crimson)' : 'var(--cyan-primary)' }} />
                  <h3 style={{ fontSize: '1.15rem', color: '#fff' }}>
                    Node Inspector: {selectedNode.type}
                  </h3>
                </div>
                <div className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem', wordBreak: 'break-all' }}>
                  {selectedNode.id}
                </div>
              </div>

              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedNode(null)}>
                <X size={16} />
              </button>
            </div>

            {/* Telemetry Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginBottom: '1.5rem' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Classification:</span>
                  <span style={{ fontWeight: 700, color: 'var(--cyan-primary)' }}>
                    {selectedNode.entity_type}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Risk Score:</span>
                  <span style={{ fontWeight: 700, color: selectedNode.risk > 0.6 ? 'var(--crimson)' : 'var(--emerald)' }}>
                    {((selectedNode.risk || 0) * 100).toFixed(0)}%
                  </span>
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
          </div>
        </div>
      )}
    </div>
  );
}
