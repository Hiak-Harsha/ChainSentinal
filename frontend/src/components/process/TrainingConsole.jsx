import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, CheckCircle2, Loader, Cpu } from 'lucide-react';

/**
 * TrainingConsole — Terminal-style real-time log stream showing AI model training stages.
 */
export default function TrainingConsole({
  active = false,
  logs = [],
  currentStage = 'Idle',
  progress = 0,
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  if (!active && logs.length === 0) return null;

  return (
    <div
      style={{
        background: '#0a0806',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        marginBottom: '1.5rem',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* Console Title Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.5rem 0.85rem',
          background: 'rgba(255, 255, 255, 0.03)',
          borderBottom: '1px solid var(--border-subtle)',
          fontSize: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Terminal size={14} style={{ color: 'var(--btc-orange)' }} />
          <span style={{ fontWeight: 700, color: 'var(--text-main)', letterSpacing: '0.04em' }}>
            ML TRAINING PIPELINE RUNTIME
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {active ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--btc-orange)' }}>
              <Loader size={12} className="animate-spin" /> {currentStage}
            </span>
          ) : (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--emerald)' }}>
              <CheckCircle2 size={12} /> Ready
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {active && (
        <div style={{ height: '3px', background: 'rgba(255, 255, 255, 0.05)', width: '100%' }}>
          <motion.div
            style={{ height: '100%', background: 'linear-gradient(90deg, var(--btc-orange), var(--btc-gold))' }}
            initial={{ width: 0 }}
            animate={{ width: `${progress * 100}%` }}
            transition={{ duration: 0.2 }}
          />
        </div>
      )}

      {/* Terminal Log Body */}
      <div
        ref={scrollRef}
        style={{
          padding: '0.75rem 1rem',
          maxHeight: '140px',
          overflowY: 'auto',
          fontFamily: '"JetBrains Mono", ui-monospace, monospace',
          fontSize: '0.72rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.35rem',
          color: 'var(--text-muted)',
        }}
      >
        {logs.map((log, idx) => (
          <div key={idx} style={{ display: 'flex', gap: '0.5rem' }}>
            <span style={{ color: 'var(--text-dim)' }}>&gt;</span>
            <span style={{ color: log.includes('complete') ? 'var(--emerald)' : log.includes('error') ? 'var(--crimson)' : 'var(--text-main)' }}>
              {log}
            </span>
          </div>
        ))}
        {active && (
          <div style={{ display: 'flex', gap: '0.5rem', color: 'var(--btc-orange)' }}>
            <span>&gt;</span>
            <span className="pulse-dot" style={{ display: 'inline-block', verticalAlign: 'middle', marginTop: '4px' }} />
          </div>
        )}
      </div>
    </div>
  );
}
