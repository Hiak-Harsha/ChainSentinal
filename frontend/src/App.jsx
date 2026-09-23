import React, { useEffect, useState, useCallback, useRef } from 'react';
import CommandBar from './components/shell/CommandBar';
import ContextRail from './components/shell/ContextRail';
import InspectorPanel from './components/shell/InspectorPanel';
import NetworkCanvas from './components/NetworkCanvas';
import OverviewView from './components/OverviewView';
import AlertCenterView from './components/AlertCenterView';
import TaintPathfinderView from './components/TaintPathfinderView';
import CasesView from './components/CasesView';
import ModelLabView from './components/ModelLabView';
import IngestWizardView from './components/IngestWizardView';
import { AnimatedLedgerBackdrop } from './components/visuals/AnimatedLedgerBackdrop';
import { ToastProvider, useToast } from './components/shared/Toast';
import { api } from './api';

function AppContent() {
  const [mode, setMode] = useState('network');
  const [selection, setSelection] = useState(null);
  const [recentEntities, setRecentEntities] = useState([]);
  const [activeCase, setActiveCase] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Selected item details for InspectorPanel
  const [entityDetail, setEntityDetail] = useState(null);
  const [similarEntities, setSimilarEntities] = useState([]);
  const [alertDetail, setAlertDetail] = useState(null);
  const [traceDetail, setTraceDetail] = useState(null);
  const [caseDetail, setCaseDetail] = useState(null);

  // App metrics & state
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [centerId, setCenterId] = useState('');
  const [hops, setHops] = useState(2);
  const [prefilledTarget, setPrefilledTarget] = useState('');
  const [detecting, setDetecting] = useState(false);
  const [liveEvents, setLiveEvents] = useState([]);

  const toast = useToast();
  const wsRef = useRef(null);

  // Load initial system data
  const refreshData = useCallback(async () => {
    try {
      const [hData, aData, mData] = await Promise.all([
        api.getHealth().catch(() => ({ status: 'error' })),
        api.getAlerts({ limit: 100 }).catch(() => []),
        api.getGraphMetrics().catch(() => null),
      ]);
      setHealth(hData);
      setAlerts(aData || []);
      setMetrics(mData);
    } catch (err) {
      console.error('Initial data fetch error:', err);
      toast?.showToast('Failed to connect to backend', 'error');
    }
  }, [toast]);

  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Live WebSocket feed
  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;

    const connectWS = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/live`;
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('[WebSocket] Live forensic feed connected');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setLiveEvents((prev) => [data, ...prev.slice(0, 99)]);

            if (data.type === 'new_alert') {
              toast?.showToast(`High-priority alert: ${data.data?.entity_id || 'Entity'}`, 'error');
              refreshData();
            } else if (data.type === 'detection_complete') {
              toast?.showToast('Inference pipeline complete', 'success');
              refreshData();
            } else if (data.type === 'cluster_merge') {
              // Cluster merge progress
            }
          } catch (e) {
            console.error('WS parse error:', e);
          }
        };

        ws.onerror = () => {
          ws?.close();
        };

        ws.onclose = () => {
          reconnectTimeout = setTimeout(connectWS, 5000);
        };

        wsRef.current = ws;
      } catch (err) {
        console.warn('WS not available, continuing with HTTP polling:', err);
      }
    };

    connectWS();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, [refreshData, toast]);

  // Pivot navigation
  const pivotTo = useCallback(({ mode: nextMode, selection: nextSelection }) => {
    if (nextMode) setMode(nextMode);
    if (nextSelection !== undefined) {
      setSelection(nextSelection);

      // Track recent entities
      if (nextSelection?.type === 'entity' && nextSelection?.id) {
        setCenterId(nextSelection.id);
        setRecentEntities((prev) => {
          const filtered = prev.filter((e) => e.entity_id !== nextSelection.id);
          const entityType = nextSelection.data?.entity_type || 'UNKNOWN';
          return [{ entity_id: nextSelection.id, entity_type: entityType }, ...filtered].slice(0, 8);
        });
      }
    }
  }, []);

  // Fetch contextual details when selection changes
  useEffect(() => {
    if (!selection) {
      setEntityDetail(null);
      setSimilarEntities([]);
      setAlertDetail(null);
      setTraceDetail(null);
      setCaseDetail(null);
      return;
    }

    if (selection.type === 'entity') {
      api.getEntityDetail(selection.id)
        .then((detail) => setEntityDetail(detail))
        .catch(() => setEntityDetail(selection.data || { entity_id: selection.id }));

      api.getSimilarEntities(selection.id, 5)
        .then((similar) => setSimilarEntities(similar || []))
        .catch(() => setSimilarEntities([]));
    } else if (selection.type === 'alert') {
      const existing = alerts.find((a) => a.alert_id === selection.id);
      if (existing) {
        setAlertDetail(existing);
      } else {
        api.getAlertDetail(selection.id)
          .then((detail) => setAlertDetail(detail))
          .catch(() => setAlertDetail(selection.data || null));
      }
    } else if (selection.type === 'trace') {
      if (selection.data) {
        setTraceDetail(selection.data);
      } else {
        api.getTrace(selection.id)
          .then((t) => setTraceDetail(t))
          .catch(() => setTraceDetail(null));
      }
    } else if (selection.type === 'case') {
      api.getCaseFile(selection.id)
        .then((c) => {
          setCaseDetail(c);
          setActiveCase(c);
        })
        .catch(() => {
          if (selection.data) {
            setCaseDetail(selection.data);
            setActiveCase(selection.data);
          }
        });
    }
  }, [selection, alerts]);

  // Global search handler
  const handleSearch = (query) => {
    setSearchQuery(query);
    if (!query) return;

    const matchedAlert = alerts.find(
      (a) =>
        a.alert_id.toLowerCase().includes(query.toLowerCase()) ||
        a.entity_id?.toLowerCase().includes(query.toLowerCase())
    );
    if (matchedAlert) {
      pivotTo({
        mode: 'alerts',
        selection: { type: 'alert', id: matchedAlert.alert_id, data: matchedAlert },
      });
      return;
    }

    // If query looks like an address or entity ID
    if (query.length >= 8) {
      pivotTo({
        mode: 'network',
        selection: { type: 'entity', id: query },
      });
      setCenterId(query);
    }
  };

  // Trigger full detection run
  const handleTriggerDetect = async () => {
    setDetecting(true);
    toast?.showToast('Executing AI inference on unflagged entities...', 'info');
    try {
      const newAlerts = await api.runDetection(0.35, 50);
      if (Array.isArray(newAlerts) && newAlerts.length > 0) {
        setAlerts(newAlerts);
        toast?.showToast(`Detection complete: ${newAlerts.length} high-risk entities identified`, 'success');
      } else {
        await refreshData();
        toast?.showToast('Detection complete: database up to date', 'success');
      }
      setMode('alerts');
    } catch (err) {
      toast?.showToast(`Detection failed: ${err.message}`, 'error');
    } finally {
      setDetecting(false);
    }
  };

  // Cross-view actions
  const handleLaunchTrace = (targetId) => {
    setPrefilledTarget(targetId);
    pivotTo({
      mode: 'taint',
      selection: { type: 'entity', id: targetId },
    });
    toast?.showToast(`Initialized forward taint trace for ${targetId.slice(0, 12)}...`, 'info');
  };

  const handleLaunchInvestigate = (targetId) => {
    setPrefilledTarget(targetId);
    pivotTo({
      mode: 'cases',
      selection: { type: 'entity', id: targetId },
    });
    toast?.showToast(`Opened case investigation dossier for ${targetId.slice(0, 12)}...`, 'info');
  };

  const handleStatusUpdated = (alertId, newStatus) => {
    setAlerts((prev) =>
      prev.map((a) => (a.alert_id === alertId ? { ...a, status: newStatus } : a))
    );
    if (alertDetail && alertDetail.alert_id === alertId) {
      setAlertDetail((prev) => ({ ...prev, status: newStatus }));
    }
    toast?.showToast(`Alert triage updated to ${newStatus.replace(/_/g, ' ')}`, 'success');
  };

  return (
    <div className="app-container">
      <AnimatedLedgerBackdrop />
      <CommandBar
        mode={mode}
        setMode={(nextMode) => pivotTo({ mode: nextMode })}
        searchQuery={searchQuery}
        onSearchChange={handleSearch}
        alertCount={alerts.length}
        entityCount={metrics?.total_entities}
        riskScore={metrics?.mean_risk_score ?? null}
        health={health}
        onAlertBellClick={() => pivotTo({ mode: 'alerts' })}
      />

      <div className="workspace-shell">
        <ContextRail
          recentEntities={recentEntities}
          activeCase={activeCase}
          selection={selection}
          onPivotTo={pivotTo}
        />

        <main className="primary-canvas">
          {/* Persistent Network Canvas */}
          <NetworkCanvas
            centerId={centerId}
            onCenterIdChange={(id) => {
              setCenterId(id);
              pivotTo({ mode: 'network', selection: { type: 'entity', id } });
            }}
            hops={hops}
            onHopsChange={setHops}
            selectedEntityId={selection?.type === 'entity' ? selection.id : null}
            onSelectEntity={(id, data) =>
              pivotTo({ mode: 'network', selection: { type: 'entity', id, data } })
            }
            onLaunchTrace={handleLaunchTrace}
            onLaunchInvestigate={handleLaunchInvestigate}
            hidden={mode !== 'network'}
          />

          {/* Mode Overlays */}
          {mode === 'overview' && (
            <div className="canvas-overlay">
              <OverviewView
                metrics={metrics}
                alerts={alerts}
                onSelectAlert={(a) =>
                  pivotTo({
                    mode: 'alerts',
                    selection: { type: 'alert', id: a.alert_id, data: a },
                  })
                }
                onSwitchTab={(t) => pivotTo({ mode: t === 'graph' ? 'network' : t })}
                onTriggerDetect={handleTriggerDetect}
                detecting={detecting}
              />
            </div>
          )}

          {mode === 'alerts' && (
            <div className="canvas-overlay">
              <AlertCenterView
                alerts={alerts}
                selectedAlert={selection?.type === 'alert' ? alertDetail : null}
                onSelectAlert={(a) =>
                  pivotTo({
                    mode: 'alerts',
                    selection: { type: 'alert', id: a.alert_id, data: a },
                  })
                }
              />
            </div>
          )}

          {mode === 'taint' && (
            <div className="canvas-overlay">
              <TaintPathfinderView
                prefilledTarget={prefilledTarget}
                onTraceCompleted={(traceResult) => {
                  if (traceResult?.trace_id) {
                    setSelection({ type: 'trace', id: traceResult.trace_id, data: traceResult });
                  }
                }}
              />
            </div>
          )}

          {mode === 'cases' && (
            <div className="canvas-overlay">
              <CasesView
                prefilledTarget={prefilledTarget}
                selectedCaseId={selection?.type === 'case' ? selection.id : null}
                onSelectCase={(c) => {
                  setActiveCase(c);
                  setSelection({ type: 'case', id: c.case_id, data: c });
                }}
              />
            </div>
          )}

          {mode === 'models' && (
            <div className="canvas-overlay">
              <ModelLabView onTriggerDetect={handleTriggerDetect} />
            </div>
          )}

          {mode === 'ingest' && (
            <div className="canvas-overlay">
              <IngestWizardView />
            </div>
          )}
        </main>

        <InspectorPanel
          selection={selection}
          onClearSelection={() => setSelection(null)}
          entityDetail={entityDetail}
          similarEntities={similarEntities}
          alertDetail={alertDetail}
          onAlertAction={handleStatusUpdated}
          traceDetail={traceDetail}
          caseDetail={caseDetail}
          onLaunchTrace={handleLaunchTrace}
          onInvestigate={handleLaunchInvestigate}
        />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}
