import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  Bell,
  Network,
  AlertTriangle,
  GitBranch,
  Cpu,
  UploadCloud,
  Shield,
  LayoutDashboard,
} from 'lucide-react';
import { ChainSentinelLogo } from '../visuals/icons';
import { AnimatedNumber } from '../shared';
import AlertSparkline from '../charts/AlertSparkline';

const MODES = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'network', label: 'Network', icon: Network },
  { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
  { id: 'taint', label: 'Taint', icon: GitBranch },
  { id: 'models', label: 'Models', icon: Cpu },
  { id: 'ingest', label: 'Ingest', icon: UploadCloud },
];

export default function CommandBar({
  mode,
  setMode,
  searchQuery,
  onSearchChange,
  alertCount = 0,
  entityCount = 0,
  riskScore = null,
  health = null,
  onAlertBellClick,
}) {
  const isOnline = health?.status === 'ok';

  return (
    <div className="command-bar">
      {/* Brand */}
      <div className="brand-compact">
        <motion.div
          layoutId="chainsentinel-brand-logo"
          className="brand-logo"
          whileHover={{ scale: 1.08, rotate: 3 }}
          transition={{ type: 'spring', stiffness: 350, damping: 18 }}
        >
          <ChainSentinelLogo size={22} />
        </motion.div>
        <span className="brand-name">ChainSentinel</span>
        <span className="brand-tag">NTRO SIH-2026</span>
      </div>

      {/* Global Search */}
      <div className="command-bar-search">
        <Search size={14} className="search-icon" />
        <input
          id="global-search-input"
          type="text"
          placeholder="Search entities, alerts, addresses\u2026"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>

      {/* Mode Switcher */}
      <div className="mode-switcher">
        {MODES.map((m) => {
          const Icon = m.icon;
          return (
            <button
              key={m.id}
              id={`mode-btn-${m.id}`}
              className={`mode-btn ${mode === m.id ? 'active' : ''}`}
              onClick={() => setMode(m.id)}
              title={m.label}
            >
              <Icon size={14} />
              <span>{m.label}</span>
            </button>
          );
        })}
      </div>

      {/* Inline KPIs */}
      <div className="command-bar-kpis">
        <div className="command-bar-kpi">
          <Shield size={13} />
          <span>Entities:</span>
          <span className="kpi-num">
            <AnimatedNumber value={entityCount} />
          </span>
        </div>
        {riskScore !== null && (
          <div className="command-bar-kpi">
            <span>Risk:</span>
            <span
              className="kpi-num"
              style={{
                color: riskScore > 0.7 ? 'var(--crimson)' : riskScore > 0.4 ? 'var(--amber)' : 'var(--emerald)',
              }}
            >
              {(riskScore * 100).toFixed(0)}%
            </span>
          </div>
        )}
        <div className="command-bar-kpi" style={{ gap: '0.45rem' }}>
          <span>Velocity:</span>
          <AlertSparkline width={100} height={22} color="var(--amber)" />
        </div>
      </div>

      {/* Status & Alert Bell */}
      <div className="command-bar-status">
        <div className="status-pill">
          <span
            className="pulse-dot"
            style={{
              backgroundColor: isOnline ? 'var(--emerald)' : '#f43f5e',
              boxShadow: `0 0 8px ${isOnline ? 'var(--emerald)' : '#f43f5e'}`,
            }}
          />
          <span style={{ color: isOnline ? 'var(--emerald)' : '#f43f5e', fontSize: '0.65rem' }}>
            {isOnline ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        <button
          className="alert-bell-btn"
          id="alert-bell-btn"
          onClick={onAlertBellClick}
          title="Open Alert Center"
        >
          <Bell size={18} />
          {alertCount > 0 && (
            <motion.span
              className="bell-count"
              initial={{ scale: 0.6 }}
              animate={{ scale: 1 }}
              key={alertCount}
            >
              {alertCount > 99 ? '99+' : alertCount}
            </motion.span>
          )}
        </button>
      </div>
    </div>
  );
}
