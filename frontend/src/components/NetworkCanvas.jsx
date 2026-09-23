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
  GitMerge,
} from 'lucide-react';
import { api } from '../api';
import { RadarEmptyState } from './visuals/RadarEmptyState';
import ClusteringVisualizer from './process/ClusteringVisualizer';

export default function NetworkCanvas({
  centerId,
  onCenterIdChange,
  hops = 2,
  onHopsChange,
  selectedEntityId = null,
  onSelectEntity,
  onLaunchTrace,
  onLaunchInvestigate,
  hidden = false,
}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  const [inputCenterId, setInputCenterId] = useState(centerId || '');
  const [currentHops, setCurrentHops] = useState(hops);
  const [layoutName, setLayoutName] = useState('cose');
  const [loading, setLoading] = useState(false);
  const [entitiesList, setEntitiesList] = useState([]);
  const [hasData, setHasData] = useState(false);

  // Entity Resolution / Clustering State
  const [clustering, setClustering] = useState(false);
  const [clusterProgress, setClusterProgress] = useState(0);
  const [clusterStage, setClusterStage] = useState('Idle');
  const [clusterEvents, setClusterEvents] = useState([]);

  const handleRunCluster = async () => {
    setClustering(true);
    setClusterProgress(0.15);
    setClusterStage('Loading Graph');
    setClusterEvents([
      { stage: 'Scan', merged: 'Extracting multi-input UTXO transactions' },
    ]);

    try {
      const res = await api.startJob('/graph/cluster', { async_mode: true });
      if (res && res.job_id) {
        setClusterStage('Union-Find Clustering');
        setClusterProgress(0.4);
        setClusterEvents((prev) => [
          { stage: 'Union-Find', merged: 'Merging co-spending addresses into clusters' },
          ...prev,
        ]);

        const interval = setInterval(async () => {
          try {
            const status = await api.getJobStatus(res.job_id);
            if (status.status === 'completed') {
              clearInterval(interval);
              setClusterProgress(1.0);
              setClusterStage('CoinJoin Check & Finalize');
              setClusterEvents((prev) => [
                { stage: 'Resolved', merged: `${status.result?.merged_entities ?? 'Multiple'} entities reconciled` },
                ...prev,
              ]);
              setTimeout(() => {
                setClustering(false);
                loadGraph(inputCenterId, currentHops);
              }, 2200);
            } else if (status.status === 'failed') {
              clearInterval(interval);
              setClustering(false);
            } else if (status.events && status.events.length > 0) {
              setClusterEvents(status.events);
              setClusterProgress((prev) => Math.min(0.9, prev + 0.15));
            }
          } catch (e) {
            clearInterval(interval);
            setClustering(false);
          }
        }, 700);
      } else {
        setClusterProgress(1.0);
        setClusterStage('Complete');
        setTimeout(() => {
          setClustering(false);
          loadGraph(inputCenterId, currentHops);
        }, 1500);
      }
    } catch (err) {
      console.error('Cluster execution error:', err);
      setClustering(false);
    }
  };

  // Sync external centerId change
  useEffect(() => {
    if (centerId && centerId !== inputCenterId) {
      setInputCenterId(centerId);
      loadGraph(centerId, currentHops);
    }
  }, [centerId]);

  // Load available entities for quick selection
  useEffect(() => {
    api.getEntities(50)
      .then((ents) => {
        if (ents && ents.length > 0) {
          setEntitiesList(ents);
          if (!centerId && !inputCenterId) {
            setInputCenterId(ents[0].entity_id);
            onCenterIdChange?.(ents[0].entity_id);
            loadGraph(ents[0].entity_id, currentHops);
          }
        }
      })
      .catch(console.error);
  }, []);

  // Update Cytoscape node selection highlighting
  useEffect(() => {
    if (cyRef.current && selectedEntityId) {
      cyRef.current.$(':selected').unselect();
      const targetNode = cyRef.current.$id(selectedEntityId);
      if (targetNode && targetNode.length > 0) {
        targetNode.select();
      }
    }
  }, [selectedEntityId]);

  // Fetch subgraph and render in Cytoscape
  const loadGraph = async (targetId, hopCount = currentHops) => {
    if (!targetId || !containerRef.current) return;
    setLoading(true);

    try {
      const data = await api.getEgoSubgraph(targetId, hopCount);
      const elements = [];

      (data.nodes || []).forEach((n) => {
        const risk = n.risk_score ?? n.risk ?? null;
        let color = '#d4a054'; // warm gold default
        if (n.type === 'IP') color = '#e8a33d';
        else if (n.type === 'Transaction') color = '#6b6259';
        else if (n.type === 'Address') color = '#00d4e0';
        else if (
          risk !== null &&
          (risk >= 0.7 || ['DARKNET', 'RANSOMWARE', 'MIXER'].includes(n.entity_type))
        )
          color = '#e05353';
        else if (risk !== null && risk >= 0.4) color = '#f7931a';
        else if (n.type === 'Entity') color = '#f7931a';

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

      if (cyRef.current) {
        cyRef.current.destroy();
      }

      setHasData(elements.length > 0);

      const cy = cytoscape({
        container: containerRef.current,
        elements: elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(bgColor)',
              'label': 'data(label)',
              'color': '#f5f0e8',
              'font-size': '10px',
              'font-family': 'monospace',
              'text-valign': 'bottom',
              'text-margin-y': 4,
              'width': 26,
              'height': 26,
              'border-width': 2,
              'border-color': 'rgba(245, 240, 232, 0.4)',
              'transition-property': 'background-color, line-color, target-arrow-color, width, height',
              'transition-duration': '0.2s',
            },
          },
          {
            selector: 'node[?isCenter]',
            style: {
              'width': 38,
              'height': 38,
              'border-width': 3,
              'border-color': '#f7931a',
              'box-shadow': '0 0 16px rgba(247, 147, 26, 0.6)',
            },
          },
          {
            selector: 'node[entity_type = "EXCHANGE"]',
            style: {
              'shape': 'hexagon',
              'width': 32,
              'height': 32,
              'background-color': '#4ade80',
              'border-color': 'rgba(74, 222, 128, 0.6)',
            },
          },
          {
            selector: 'node[entity_type = "MIXER"], node[entity_type = "DARKNET"]',
            style: {
              'shape': 'diamond',
              'width': 30,
              'height': 30,
              'background-color': '#e05353',
              'border-color': 'rgba(224, 83, 83, 0.6)',
            },
          },
          {
            selector: 'node[type = "IP"]',
            style: {
              'shape': 'octagon',
              'width': 26,
              'height': 26,
              'background-color': '#e8a33d',
            },
          },
          {
            selector: 'node[type = "Transaction"]',
            style: {
              'shape': 'round-rectangle',
              'width': 26,
              'height': 16,
              'background-color': '#6b6259',
              'border-color': 'rgba(245, 240, 232, 0.25)',
            },
          },
          {
            selector: 'edge',
            style: {
              'width': 1.6,
              'line-color': 'rgba(245, 240, 232, 0.18)',
              'target-arrow-color': 'rgba(245, 240, 232, 0.35)',
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
              'border-color': '#f7931a',
              'box-shadow': '0 0 16px rgba(247, 147, 26, 0.8)',
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
        const nodeData = node.data();
        onSelectEntity?.(nodeData.id, nodeData);
      });

      cyRef.current = cy;
    } catch (err) {
      console.error('Failed to load subgraph:', err);
    } finally {
      setLoading(false);
    }
  };

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
    <div
      className="network-canvas-container"
      style={{
        display: hidden ? 'none' : 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        position: 'relative',
        background: 'var(--bg-base)',
      }}
    >
      {/* Top Action/Control Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
          padding: '0.6rem 1rem',
          background: 'rgba(18, 14, 10, 0.95)',
          borderBottom: '1px solid var(--border-subtle)',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '280px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={14}
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-dim)',
              }}
            />
            <input
              type="text"
              className="input mono"
              style={{ width: '100%', paddingLeft: '2.25rem', fontSize: '0.8rem', height: '34px' }}
              placeholder="Search or enter Entity ID / Address\u2026"
              value={inputCenterId}
              onChange={(e) => setInputCenterId(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  onCenterIdChange?.(inputCenterId);
                  loadGraph(inputCenterId, currentHops);
                }
              }}
            />
          </div>

          <button
            className="btn btn-primary"
            style={{ height: '34px', padding: '0 0.8rem', fontSize: '0.78rem' }}
            onClick={() => {
              onCenterIdChange?.(inputCenterId);
              loadGraph(inputCenterId, currentHops);
            }}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Loading\u2026' : 'Expand'}
          </button>
        </div>

        {/* Layout & Hop Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <Layers size={14} />
            <select
              className="select"
              style={{ height: '32px', fontSize: '0.78rem' }}
              value={layoutName}
              onChange={(e) => setLayoutName(e.target.value)}
            >
              <option value="cose">Force-Directed</option>
              <option value="concentric">Concentric</option>
              <option value="circle">Circular</option>
              <option value="grid">Grid</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <Sliders size={14} />
            <select
              className="select"
              style={{ height: '32px', fontSize: '0.78rem' }}
              value={currentHops}
              onChange={(e) => {
                const val = parseInt(e.target.value);
                setCurrentHops(val);
                onHopsChange?.(val);
                loadGraph(inputCenterId, val);
              }}
            >
              <option value={1}>1 Hop</option>
              <option value={2}>2 Hops</option>
              <option value={3}>3 Hops</option>
            </select>
          </div>

          {/* Quick Entities */}
          {entitiesList.length > 0 && (
            <select
              className="select"
              style={{ height: '32px', fontSize: '0.78rem', maxWidth: '160px' }}
              value={inputCenterId}
              onChange={(e) => {
                setInputCenterId(e.target.value);
                onCenterIdChange?.(e.target.value);
                loadGraph(e.target.value, currentHops);
              }}
            >
              <option value="" disabled>Pivots…</option>
              {entitiesList.map((ent) => (
                <option key={ent.entity_id} value={ent.entity_id}>
                  {ent.entity_id.slice(0, 10)}… ({ent.entity_type})
                </option>
              ))}
            </select>
          )}

          {/* Entity Resolution Action */}
          <button
            id="btn-run-clustering"
            className="btn btn-secondary"
            style={{ height: '32px', padding: '0 0.65rem', fontSize: '0.75rem', gap: '0.35rem' }}
            onClick={handleRunCluster}
            disabled={clustering}
            title="Execute Union-Find multi-input clustering"
          >
            <GitMerge size={13} style={{ color: 'var(--btc-orange)' }} />
            <span>{clustering ? 'Clustering…' : 'Cluster'}</span>
          </button>
        </div>
      </div>

      {/* Cytoscape Viewport */}
      <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
        {clustering && (
          <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 30, maxWidth: '380px', width: '100%' }}>
            <ClusteringVisualizer
              active={clustering}
              progress={clusterProgress}
              stage={clusterStage}
              mergeEvents={clusterEvents}
            />
          </div>
        )}
        <div
          ref={containerRef}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
          }}
        />

        {/* Empty state if no data */}
        {!hasData && !loading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'var(--bg-base)',
              zIndex: 2,
            }}
          >
            <RadarEmptyState
              title="NETWORK CANVAS READY"
              subtitle="Select an entity or search an address/TXID to expand forensic graph topology."
            />
          </div>
        )}

        {/* Viewport Floating Controls */}
        <div
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            zIndex: 10,
            display: 'flex',
            gap: '6px',
          }}
        >
          <button className="btn btn-secondary btn-sm" onClick={() => handleZoom(1.25)} title="Zoom In">
            <ZoomIn size={13} />
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => handleZoom(0.8)} title="Zoom Out">
            <ZoomOut size={13} />
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handleFit} title="Fit to Viewport">
            <Maximize2 size={13} />
          </button>
        </div>

        {/* Legend */}
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            zIndex: 10,
            background: 'rgba(18, 14, 10, 0.92)',
            padding: '0.45rem 0.75rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.68rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.3rem',
            backdropFilter: 'blur(8px)',
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.04em' }}>TOPOLOGY LEGEND</div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ade80' }} /> Exchange
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#e05353' }} /> Mixer / High Risk
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f7931a' }} /> Focal Entity
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00d4e0' }} /> Address
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
