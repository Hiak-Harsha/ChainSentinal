import React from 'react';
import { BlockLedgerIcon, BTCCoinIcon, WalletClusterIcon } from './icons';

/**
 * PipelineFlowDiagram
 * 4-stage data ingest visual showing:
 * Raw Ingest -> Streaming Parser -> DuckDB Graph Store -> CIOH & Taint Validated
 */
export const PipelineFlowDiagram = ({ currentStep = 1, fileCount = 0 }) => {
  const steps = [
    {
      id: 1,
      title: 'Raw Ingest',
      subtitle: `${fileCount > 0 ? `${fileCount} Files Staged` : 'CSV / JSON / DAT'}`,
      icon: (color) => (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.7">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="15" y2="15" />
        </svg>
      ),
    },
    {
      id: 2,
      title: 'Streaming Parser',
      subtitle: 'UTXO & Script Decoder',
      icon: (color) => <BlockLedgerIcon size={20} color={color} />,
    },
    {
      id: 3,
      title: 'DuckDB Engine',
      subtitle: 'Vector & Columnar Graph',
      icon: (color) => <BTCCoinIcon size={20} color={color} />,
    },
    {
      id: 4,
      title: 'Forensic Graph',
      subtitle: 'CIOH & Taint Ready',
      icon: (color) => <WalletClusterIcon size={20} color={color} />,
    },
  ];

  return (
    <div style={{ marginBottom: '1.75rem' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '0.85rem',
          position: 'relative',
        }}
      >
        {steps.map((step) => {
          const isCompleted = currentStep > step.id;
          const isActive = currentStep === step.id;
          const isUpcoming = currentStep < step.id;

          let borderColor = 'var(--border-subtle)';
          let bgColor = 'rgba(15, 23, 42, 0.5)';
          let iconColor = 'var(--text-dim)';

          if (isCompleted) {
            borderColor = 'rgba(16, 185, 129, 0.4)';
            bgColor = 'rgba(16, 185, 129, 0.06)';
            iconColor = 'var(--emerald)';
          } else if (isActive) {
            borderColor = 'var(--cyan-primary)';
            bgColor = 'rgba(0, 242, 254, 0.08)';
            iconColor = 'var(--cyan-primary)';
          }

          return (
            <div
              key={step.id}
              className={`pipeline-flow-step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              style={{
                borderColor,
                backgroundColor: bgColor,
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: isActive ? 'rgba(0, 242, 254, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                  flexShrink: 0,
                }}
              >
                {step.icon(iconColor)}
              </div>

              <div style={{ overflow: 'hidden' }}>
                <div
                  style={{
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    color: isActive ? 'var(--cyan-primary)' : isCompleted ? 'var(--emerald)' : 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                  }}
                >
                  {step.id}. {step.title}
                </div>
                <div
                  style={{
                    fontSize: '0.68rem',
                    color: 'var(--text-dim)',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                    marginTop: '0.15rem',
                  }}
                >
                  {isCompleted ? 'Validated ✓' : step.subtitle}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
