import React from 'react';
import {
  ShieldAlert,
  LayoutDashboard,
  AlertTriangle,
  Network,
  GitBranch,
  FileText,
  Cpu,
  UploadCloud,
  CheckCircle2,
  Lock,
} from 'lucide-react';

export default function Header({ activeTab, setActiveTab, alertCount = 0, health = null }) {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'alerts', label: 'Alert Center', icon: AlertTriangle, badge: alertCount },
    { id: 'graph', label: 'Link Analysis', icon: Network },
    { id: 'trace', label: 'Taint & Pathfinder', icon: GitBranch },
    { id: 'cases', label: 'Case Files', icon: FileText },
    { id: 'models', label: 'Model Lab', icon: Cpu },
    { id: 'ingest', label: 'Ingest Wizard', icon: UploadCloud },
  ];

  return (
    <header>
      <div className="app-header">
        <div className="brand-section">
          <div className="brand-logo">
            <ShieldAlert size={22} />
          </div>
          <div className="brand-titles">
            <div className="brand-name">
              ChainSentinel
              <span className="brand-tag">NTRO SIH-2026</span>
            </div>
            <div className="brand-sub">
              AI-Powered Bitcoin Forensic Link Analysis & Transaction Monitoring
            </div>
          </div>
        </div>

        <div className="header-status-bar">
          <div className="status-pill">
            <span className="pulse-dot"></span>
            <span style={{ color: 'var(--emerald)' }}>
              {health?.status === 'ok' ? 'BACKEND ONLINE' : 'CONNECTING...'}
            </span>
          </div>

          <div className="status-pill">
            <Lock size={13} style={{ color: 'var(--cyan-primary)' }} />
            <span>STRICT OFFLINE (AIR-GAPPED)</span>
          </div>

          <div className="status-pill">
            <CheckCircle2 size={13} style={{ color: 'var(--purple-primary)' }} />
            <span>MODELS: {health?.models_loaded !== undefined ? `${health.models_loaded} ACTIVE` : 'READY'}</span>
          </div>
        </div>
      </div>

      <nav className="app-nav">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              id={`tab-btn-${tab.id}`}
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
              {tab.badge > 0 && <span className="nav-tab-badge">{tab.badge}</span>}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
