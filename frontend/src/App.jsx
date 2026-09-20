import React, { useEffect, useState } from 'react';
import Header from './components/Header';
import OverviewView from './components/OverviewView';
import AlertCenterView from './components/AlertCenterView';
import GraphCanvasView from './components/GraphCanvasView';
import TaintPathfinderView from './components/TaintPathfinderView';
import CasesView from './components/CasesView';
import ModelLabView from './components/ModelLabView';
import IngestWizardView from './components/IngestWizardView';
import { api } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [prefilledTarget, setPrefilledTarget] = useState('');
  const [detecting, setDetecting] = useState(false);

  // Load initial system data
  const refreshData = async () => {
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
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  // Trigger full detection run
  const handleTriggerDetect = async () => {
    setDetecting(true);
    try {
      const newAlerts = await api.runDetection(0.35, 50);
      if (Array.isArray(newAlerts) && newAlerts.length > 0) {
        setAlerts(newAlerts);
      } else {
        await refreshData();
      }
      setActiveTab('alerts');
    } catch (err) {
      alert(`Detection trigger failed: ${err.message}`);
    } finally {
      setDetecting(false);
    }
  };

  // Cross-tab navigations
  const handleLaunchTrace = (targetId) => {
    setPrefilledTarget(targetId);
    setSelectedAlert(null);
    setActiveTab('trace');
  };

  const handleLaunchInvestigate = (targetId) => {
    setPrefilledTarget(targetId);
    setSelectedAlert(null);
    setActiveTab('cases');
  };

  const handleStatusUpdated = (alertId, newStatus) => {
    setAlerts((prev) =>
      prev.map((a) => (a.alert_id === alertId ? { ...a, status: newStatus } : a))
    );
    if (selectedAlert && selectedAlert.alert_id === alertId) {
      setSelectedAlert((prev) => ({ ...prev, status: newStatus }));
    }
  };

  return (
    <div className="app-container">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        alertCount={alerts.length}
        health={health}
      />

      <main className="app-main">
        {activeTab === 'overview' && (
          <OverviewView
            metrics={metrics}
            alerts={alerts}
            onSelectAlert={setSelectedAlert}
            onSwitchTab={setActiveTab}
            onTriggerDetect={handleTriggerDetect}
            detecting={detecting}
          />
        )}

        {activeTab === 'alerts' && (
          <AlertCenterView
            alerts={alerts}
            selectedAlert={selectedAlert}
            onSelectAlert={setSelectedAlert}
            onCloseDetail={() => setSelectedAlert(null)}
            onLaunchTrace={handleLaunchTrace}
            onLaunchInvestigate={handleLaunchInvestigate}
            onStatusUpdated={handleStatusUpdated}
          />
        )}

        {activeTab === 'graph' && (
          <GraphCanvasView
            initialCenterId={prefilledTarget}
            onLaunchTrace={handleLaunchTrace}
            onLaunchInvestigate={handleLaunchInvestigate}
          />
        )}

        {activeTab === 'trace' && (
          <TaintPathfinderView prefilledTarget={prefilledTarget} />
        )}

        {activeTab === 'cases' && (
          <CasesView prefilledTarget={prefilledTarget} />
        )}

        {activeTab === 'models' && (
          <ModelLabView onTriggerDetect={handleTriggerDetect} />
        )}

        {activeTab === 'ingest' && <IngestWizardView />}
      </main>
    </div>
  );
}
