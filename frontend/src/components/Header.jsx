import React from 'react';
import { motion } from 'framer-motion';
import {
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
import { ChainSentinelLogo, BTCCoinIcon } from './visuals/icons';

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

  const isOnline = health?.status === 'ok';

  return (
    <header>
      <div className="app-header">
        <div className="brand-section">
          <motion.div
            className="brand-logo"
            initial={{ scale: 0.8, rotate: -10, opacity: 0 }}
            animate={{ scale: 1, rotate: 0, opacity: 1 }}
            whileHover={{ scale: 1.08, rotate: 3 }}
            transition={{ type: 'spring', stiffness: 350, damping: 18 }}
            style={{ background: 'transparent', border: 'none', boxShadow: 'none' }}
          >
            <ChainSentinelLogo size={36} />
          </motion.div>
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
          <div className="status-pill" style={{ borderColor: 'rgba(247, 147, 26, 0.3)', background: 'rgba(247, 147, 26, 0.08)' }}>
            <BTCCoinIcon size={14} />
            <span style={{ color: 'var(--btc-orange)', fontWeight: 700 }}>BTC MEMPOOL MONITOR</span>
          </div>

          <div className="status-pill">
            <span
              className="pulse-dot"
              style={{
                backgroundColor: isOnline ? 'var(--emerald, #10b981)' : '#f43f5e',
                boxShadow: `0 0 8px ${isOnline ? 'var(--emerald, #10b981)' : '#f43f5e'}`,
              }}
            />
            <span style={{ color: isOnline ? 'var(--emerald, #10b981)' : '#f43f5e' }}>
              {isOnline ? 'BACKEND ONLINE' : 'OFFLINE / DISCONNECTED'}
            </span>
          </div>

          <div className="status-pill">
            <Lock size={13} style={{ color: 'var(--cyan-primary)' }} />
            <span>STRICT AIR-GAP ISOLATION</span>
          </div>

          <div className="status-pill">
            <CheckCircle2 size={13} style={{ color: 'var(--purple-primary)' }} />
            <span>MODELS: {health?.models_loaded !== undefined ? `${health.models_loaded} ACTIVE` : 'READY'}</span>
          </div>
        </div>
      </div>

      <nav className="app-nav" style={{ position: 'relative' }}>
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              id={`tab-btn-${tab.id}`}
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              style={{ position: 'relative', zIndex: 1 }}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNavTabIndicator"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    backgroundColor: 'rgba(0, 240, 255, 0.08)',
                    borderRadius: '6px',
                    borderBottom: '2px solid var(--cyan-primary)',
                    zIndex: -1,
                  }}
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              <Icon size={16} />
              <span>{tab.label}</span>
              {tab.badge > 0 && (
                <motion.span
                  className="nav-tab-badge"
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  key={tab.badge}
                >
                  {tab.badge}
                </motion.span>
              )}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
