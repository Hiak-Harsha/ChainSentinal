import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Command,
  CornerDownLeft,
  X,
  Shield,
  AlertTriangle,
  FolderOpen,
  Keyboard,
  ArrowRight,
  Clock,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import { api } from '../../api';

export default function CommandPalette({
  isOpen,
  onClose,
  onSelect,
  alerts = [],
  recentEntities = [],
  cases = [],
}) {
  const [query, setQuery] = useState('');
  const [remoteEntities, setRemoteEntities] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selectedIndexRef = useRef(0);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      selectedIndexRef.current = 0;
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Debounced remote entity search
  useEffect(() => {
    if (!isOpen || !query.trim() || query.trim().length < 2) {
      setRemoteEntities([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const results = await api.getEntities({ search: query.trim(), limit: 8 });
        setRemoteEntities(results || []);
      } catch (err) {
        console.warn('CommandPalette entity search error:', err);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [query, isOpen]);

  // Filter and group results across Entities, Alerts, Cases
  const { results, flatList } = useMemo(() => {
    const q = query.toLowerCase().trim();

    // 1. Entities
    let matchedEntities = [];
    if (!q) {
      matchedEntities = recentEntities.slice(0, 6).map((e) => ({
        id: e.entity_id,
        category: 'Entities',
        title: e.entity_id,
        subtitle: `Type: ${e.entity_type || 'CLUSTER'} • Recent Activity`,
        type: 'entity',
        icon: Shield,
        raw: e,
      }));
    } else {
      const combined = [
        ...recentEntities.filter((e) => e.entity_id.toLowerCase().includes(q)),
        ...remoteEntities,
      ];
      // Deduplicate by entity_id
      const seen = new Set();
      matchedEntities = combined
        .filter((e) => {
          const id = e.entity_id;
          if (seen.has(id)) return false;
          seen.add(id);
          return true;
        })
        .slice(0, 6)
        .map((e) => ({
          id: e.entity_id,
          category: 'Entities',
          title: e.entity_id,
          subtitle: `Type: ${e.entity_type || 'CLUSTER'}${e.member_count ? ` • ${e.member_count} addrs` : ''}`,
          type: 'entity',
          icon: Shield,
          raw: e,
        }));
    }

    // 2. Alerts
    const matchedAlerts = alerts
      .filter((a) => {
        if (!q) return true;
        return (
          a.alert_id?.toLowerCase().includes(q) ||
          a.entity_id?.toLowerCase().includes(q) ||
          a.typology?.toLowerCase().includes(q) ||
          a.status?.toLowerCase().includes(q)
        );
      })
      .slice(0, 5)
      .map((a) => ({
        id: a.alert_id,
        category: 'Alerts',
        title: `${a.alert_id} (${a.typology || 'Suspicious Pattern'})`,
        subtitle: `Target: ${a.entity_id || 'Unknown'} • Risk: ${typeof a.risk_score === 'number' ? Math.round(a.risk_score * 100) : 'N/A'}%`,
        type: 'alert',
        icon: AlertTriangle,
        raw: a,
      }));

    // 3. Cases
    const matchedCases = cases
      .filter((c) => {
        const cData = c.case_data || c;
        if (!q) return true;
        return (
          cData.case_id?.toLowerCase().includes(q) ||
          cData.target_id?.toLowerCase().includes(q) ||
          cData.title?.toLowerCase().includes(q)
        );
      })
      .slice(0, 5)
      .map((c) => {
        const cData = c.case_data || c;
        return {
          id: cData.case_id,
          category: 'Cases',
          title: cData.title || `Dossier ${cData.case_id}`,
          subtitle: `Target: ${cData.target_id || ''} • Status: ${cData.status || 'OPEN'}`,
          type: 'case',
          icon: FolderOpen,
          raw: cData,
        };
      });

    const flat = [...matchedEntities, ...matchedAlerts, ...matchedCases];

    return {
      results: {
        Entities: matchedEntities,
        Alerts: matchedAlerts,
        Cases: matchedCases,
      },
      flatList: flat,
    };
  }, [query, recentEntities, remoteEntities, alerts, cases]);

  // Keep selected index in bounds
  useEffect(() => {
    if (selectedIndex >= flatList.length) {
      setSelectedIndex(Math.max(0, flatList.length - 1));
    }
  }, [flatList.length, selectedIndex]);

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const next = (selectedIndexRef.current + 1) % Math.max(1, flatList.length);
      selectedIndexRef.current = next;
      setSelectedIndex(next);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const next = (selectedIndexRef.current - 1 + flatList.length) % Math.max(1, flatList.length);
      selectedIndexRef.current = next;
      setSelectedIndex(next);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const item = flatList[selectedIndexRef.current] || flatList[selectedIndex];
      if (item) {
        handleSelectItem(item);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      if (showShortcuts) {
        setShowShortcuts(false);
      } else {
        onClose();
      }
    }
  };

  const handleSelectItem = (item) => {
    if (!item) return;
    if (item.type === 'entity') {
      onSelect({
        mode: 'network',
        selection: { type: 'entity', id: item.id, data: item.raw },
      });
    } else if (item.type === 'alert') {
      onSelect({
        mode: 'alerts',
        selection: { type: 'alert', id: item.id, data: item.raw },
      });
    } else if (item.type === 'case') {
      onSelect({
        mode: 'cases',
        selection: { type: 'case', id: item.id, data: item.raw },
      });
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div
        className="command-palette-backdrop"
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(5, 8, 15, 0.78)',
          backdropFilter: 'blur(8px)',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'center',
          paddingTop: '12vh',
        }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -10 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          onClick={(e) => e.stopPropagation()}
          style={{
            width: '100%',
            maxWidth: '640px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-focus)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 20px 48px -10px rgba(0, 0, 0, 0.7), 0 0 1px 1px rgba(247, 147, 26, 0.15)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Search Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '0.85rem 1rem',
              borderBottom: '1px solid var(--border-subtle)',
              gap: '0.75rem',
              background: 'var(--bg-elevated)',
            }}
          >
            <Search size={18} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <input
              ref={inputRef}
              type="text"
              placeholder="Type to search entities, alerts, or cases... (↑/↓ to navigate)"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--text-main)',
                fontSize: '0.95rem',
                fontFamily: 'inherit',
              }}
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-dim)',
                  cursor: 'pointer',
                  padding: '2px',
                }}
              >
                <X size={14} />
              </button>
            )}
            <button
              onClick={() => setShowShortcuts((s) => !s)}
              title="Keyboard Shortcuts (?)"
              style={{
                background: 'transparent',
                border: 'none',
                color: showShortcuts ? 'var(--color-primary)' : 'var(--text-dim)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '3px 6px',
                borderRadius: '4px',
              }}
            >
              <HelpCircle size={15} />
            </button>
          </div>

          {/* Results List */}
          <div
            ref={listRef}
            style={{
              maxHeight: '380px',
              overflowY: 'auto',
              padding: '0.5rem 0',
            }}
          >
            {flatList.length === 0 ? (
              <div
                style={{
                  padding: '2.5rem 1.5rem',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '0.88rem',
                }}
              >
                No matching entities, alerts, or cases found for "{query}".
              </div>
            ) : (
              Object.entries(results).map(([category, items]) => {
                if (items.length === 0) return null;
                return (
                  <div key={category} style={{ marginBottom: '0.5rem' }}>
                    <div
                      style={{
                        padding: '0.35rem 1rem',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        color: 'var(--text-dim)',
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <span>{category}</span>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                        {items.length} result{items.length !== 1 ? 's' : ''}
                      </span>
                    </div>

                    {items.map((item) => {
                      const itemGlobalIndex = flatList.findIndex((fi) => fi.id === item.id && fi.category === item.category);
                      const isSelected = itemGlobalIndex === selectedIndex;
                      const Icon = item.icon;

                      return (
                        <div
                          key={`${item.category}-${item.id}`}
                          onClick={() => handleSelectItem(item)}
                          onMouseEnter={() => setSelectedIndex(itemGlobalIndex)}
                          style={{
                            padding: '0.55rem 1rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            cursor: 'pointer',
                            background: isSelected ? 'var(--bg-elevated)' : 'transparent',
                            borderLeft: isSelected ? '3px solid var(--color-primary)' : '3px solid transparent',
                            transition: 'background 0.1s ease',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 }}>
                            <div
                              style={{
                                width: '28px',
                                height: '28px',
                                borderRadius: 'var(--radius-sm)',
                                background: isSelected ? 'rgba(247, 147, 26, 0.15)' : 'var(--bg-surface)',
                                border: '1px solid var(--border-subtle)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                                color: isSelected ? 'var(--color-primary)' : 'var(--text-muted)',
                              }}
                            >
                              <Icon size={14} />
                            </div>
                            <div style={{ minWidth: 0 }}>
                              <div
                                style={{
                                  fontSize: '0.85rem',
                                  fontWeight: 600,
                                  color: isSelected ? 'var(--text-emphasis)' : 'var(--text-main)',
                                  whiteSpace: 'nowrap',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                }}
                              >
                                {item.title}
                              </div>
                              <div
                                style={{
                                  fontSize: '0.74rem',
                                  color: 'var(--text-dim)',
                                  whiteSpace: 'nowrap',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                }}
                              >
                                {item.subtitle}
                              </div>
                            </div>
                          </div>

                          {isSelected && (
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                                color: 'var(--text-dim)',
                                fontSize: '0.72rem',
                                flexShrink: 0,
                                marginLeft: '0.5rem',
                              }}
                            >
                              <span>Inspect</span>
                              <CornerDownLeft size={11} />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer Bar */}
          <div
            style={{
              padding: '0.55rem 1rem',
              borderTop: '1px solid var(--border-subtle)',
              background: 'var(--bg-elevated)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.73rem',
              color: 'var(--text-dim)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span>
                <kbd style={kbdStyle}>↑</kbd> <kbd style={kbdStyle}>↓</kbd> Navigate
              </span>
              <span>
                <kbd style={kbdStyle}>↵</kbd> Select
              </span>
              <span>
                <kbd style={kbdStyle}>ESC</kbd> Close
              </span>
            </div>
            <button
              onClick={() => setShowShortcuts(true)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--color-primary)',
                fontSize: '0.73rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
              }}
            >
              <Keyboard size={12} />
              <span>Shortcuts (?)</span>
            </button>
          </div>
        </motion.div>

        {/* Keyboard Shortcuts Modal */}
        <AnimatePresence>
          {showShortcuts && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              onClick={(e) => e.stopPropagation()}
              style={{
                position: 'fixed',
                top: '20vh',
                width: '100%',
                maxWidth: '460px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-focus-neutral)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: '0 24px 60px rgba(0, 0, 0, 0.8)',
                zIndex: 10000,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  padding: '0.85rem 1.15rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: 'var(--bg-elevated)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.88rem' }}>
                  <Keyboard size={16} style={{ color: 'var(--color-primary)' }} />
                  <span>Analyst Keyboard Shortcuts</span>
                </div>
                <button
                  onClick={() => setShowShortcuts(false)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
                >
                  <X size={15} />
                </button>
              </div>

              <div style={{ padding: '1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <ShortcutRow keys={['Cmd / Ctrl', 'K']} desc="Open Command Palette & Live Search" />
                <ShortcutRow keys={['?']} desc="Toggle Keyboard Shortcuts Cheat Sheet" />
                <ShortcutRow keys={['ESC']} desc="Close Palette / Deselect Node" />
                <ShortcutRow keys={['↑', '↓']} desc="Navigate List Results" />
                <ShortcutRow keys={['Enter']} desc="Select & Pivot to Target" />
                <ShortcutRow keys={['1', '—', '6']} desc="Direct Mode Switch (Overview, Graph, Alerts, Taint, Models, Ingest)" />
              </div>

              <div
                style={{
                  padding: '0.65rem 1.15rem',
                  borderTop: '1px solid var(--border-subtle)',
                  background: 'var(--bg-elevated)',
                  textAlign: 'right',
                }}
              >
                <button className="btn btn-secondary btn-sm" onClick={() => setShowShortcuts(false)}>
                  Close
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AnimatePresence>
  );
}

function ShortcutRow({ keys, desc }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span style={{ fontSize: '0.82rem', color: 'var(--text-main)' }}>{desc}</span>
      <div style={{ display: 'flex', gap: '4px' }}>
        {keys.map((k, i) => (
          <kbd key={i} style={kbdStyle}>
            {k}
          </kbd>
        ))}
      </div>
    </div>
  );
}

const kbdStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: '0.7rem',
  padding: '2px 6px',
  borderRadius: '4px',
  background: 'var(--bg-surface)',
  border: '1px solid var(--border-subtle)',
  color: 'var(--text-emphasis)',
  boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
};
