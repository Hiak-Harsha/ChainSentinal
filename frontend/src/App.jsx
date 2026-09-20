import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Header from './components/Header';
import OverviewView from './components/OverviewView';
import AlertCenterView from './components/AlertCenterView';
import GraphCanvasView from './components/GraphCanvasView';
import TaintPathfinderView from './components/TaintPathfinderView';
import CasesView from './components/CasesView';
import ModelLabView from './components/ModelLabView';
import IngestWizardView from './components/IngestWizardView';
import { AnimatedLedgerBackdrop } from './components/visuals/AnimatedLedgerBackdrop';
import { ToastProvider, useToast } from './components/shared/Toast';
import { api } from './api';

function AppContent() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [prefilledTarget, setPrefilledTarget] = useState('');
  const [detecting, setDetecting] = useState(false);
  const toast = useToast();

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
      toast?.showToast('Failed to connect to offline backend', 'error');
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

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
      setActiveTab('alerts');
    } catch (err) {
      toast?.showToast(`Detection failed: ${err.message}`, 'error');
    } finally {
      setDetecting(false);
    }
  };

  // Cross-tab navigations
  const handleLaunchTrace = (targetId) => {
    setPrefilledTarget(targetId);
    setSelectedAlert(null);
    setActiveTab('trace');
    toast?.showToast(`Initialized forward taint trace for ${targetId.slice(0, 12)}...`, 'info');
  };

  const handleLaunchInvestigate = (targetId) => {
    setPrefilledTarget(targetId);
    setSelectedAlert(null);
    setActiveTab('cases');
    toast?.showToast(`Opened case investigation dossier for ${targetId.slice(0, 12)}...`, 'info');
  };

  const handleStatusUpdated = (alertId, newStatus) => {
    setAlerts((prev) =>
      prev.map((a) => (a.alert_id === alertId ? { ...a, status: newStatus } : a))
    );
    if (selectedAlert && selectedAlert.alert_id === alertId) {
      setSelectedAlert((prev) => ({ ...prev, status: newStatus }));
    }
    toast?.showToast(`Alert triage updated to ${newStatus.replace(/_/g, ' ')}`, 'success');
  };

  return (
    <div className="app-container">
      <AnimatedLedgerBackdrop />
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        alertCount={alerts.length}
        health={health}
      />

      <main className="app-main" style={{ position: 'relative', overflow: 'hidden' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            style={{ width: '100%', height: '100%' }}
          >
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
          </motion.div>
        </AnimatePresence>
      </main>
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
