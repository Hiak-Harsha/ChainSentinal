import React, { useState } from 'react';
import { BTCCoinIcon, BlockLedgerIcon, TaintFlowIcon } from './icons';

/**
 * MiniTransactionFlow
 * Interactive forensic transaction anatomy schematic.
 * Demonstrates UTXO decomposition, change identification, and taint propagation.
 */
export const MiniTransactionFlow = ({
  txHash = '3a9c7f12e8b0...d491',
  inputBtc = '0.8500',
  changeBtc = '0.1200',
  forwardBtc = '0.7298',
  feeBtc = '0.0002',
  taintScore = 88,
}) => {
  const [activeNode, setActiveNode] = useState(null);

  return (
    <div
      style={{
        padding: '1.2rem',
        borderRadius: 'var(--radius-lg)',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(11, 17, 32, 0.95))',
        border: '1px solid rgba(0, 242, 254, 0.18)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div className="kpi-icon-wrap btc" style={{ width: 28, height: 28 }}>
            <BTCCoinIcon size={16} />
          </div>
          <div>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '0.02em' }}>
              BITCOIN UTXO DECOMPOSITION
            </span>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'monospace' }}>
              txid: {txHash}
            </div>
          </div>
        </div>

        <div className="btc-badge">
          <TaintFlowIcon size={12} color="#ef4444" />
          <span>TAINT PROPAGATION: {taintScore}%</span>
        </div>
      </div>

      {/* Schematic Diagram Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1.3fr auto 1fr',
          alignItems: 'center',
          gap: '0.75rem',
        }}
      >
        {/* Step 1: Input UTXO */}
        <div
          onMouseEnter={() => setActiveNode('input')}
          onMouseLeave={() => setActiveNode(null)}
          style={{
            padding: '0.75rem',
            borderRadius: 'var(--radius-md)',
            background: activeNode === 'input' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(15, 23, 42, 0.7)',
            border: `1px solid ${activeNode === 'input' ? 'var(--blue-primary)' : 'rgba(59, 130, 246, 0.3)'}`,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <div style={{ fontSize: '0.68rem', color: 'var(--blue-primary)', fontWeight: 700, marginBottom: '0.2rem' }}>
            INPUT UTXO [0]
          </div>
          <div style={{ fontSize: '1rem', fontWeight: 800, color: '#ffffff', fontFamily: 'monospace' }}>
            {inputBtc} <span style={{ fontSize: '0.75rem', color: 'var(--btc-orange)' }}>BTC</span>
          </div>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
            Cluster: 1A1zP...9c4
          </div>
        </div>

        {/* Arrow 1 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div className="satoshi-packet" style={{ color: 'var(--btc-orange)', fontSize: '0.7rem' }}>
            ●
          </div>
          <div style={{ width: '24px', height: '2px', background: 'rgba(0, 242, 254, 0.3)' }} />
        </div>

        {/* Step 2: Transaction Core */}
        <div
          onMouseEnter={() => setActiveNode('tx')}
          onMouseLeave={() => setActiveNode(null)}
          style={{
            padding: '0.75rem',
            borderRadius: 'var(--radius-md)',
            background: activeNode === 'tx' ? 'var(--btc-orange-subtle)' : 'rgba(18, 14, 10, 0.8)',
            border: `1px solid ${activeNode === 'tx' ? 'var(--btc-orange)' : 'rgba(247, 147, 26, 0.35)'}`,
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.3rem' }}>
            <BlockLedgerIcon size={22} color="var(--btc-orange)" />
          </div>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--btc-orange)' }}>
            1-IN / 2-OUT
          </div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
            Fee: {feeBtc} BTC
          </div>
        </div>

        {/* Arrow 2 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div className="satoshi-packet" style={{ color: 'var(--crimson)', fontSize: '0.7rem' }}>
            ●
          </div>
          <div style={{ width: '24px', height: '2px', background: 'rgba(239, 68, 68, 0.4)' }} />
        </div>

        {/* Step 3: Outputs (Peel Change & Taint) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {/* Change Output */}
          <div
            onMouseEnter={() => setActiveNode('change')}
            onMouseLeave={() => setActiveNode(null)}
            style={{
              padding: '0.5rem 0.65rem',
              borderRadius: 'var(--radius-sm)',
              background: activeNode === 'change' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${activeNode === 'change' ? 'var(--emerald)' : 'rgba(16, 185, 129, 0.25)'}`,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ fontSize: '0.62rem', color: 'var(--emerald)', fontWeight: 700 }}>
              CHANGE (PEEL)
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#ffffff', fontFamily: 'monospace' }}>
              {changeBtc} <span style={{ fontSize: '0.68rem', color: 'var(--btc-orange)' }}>BTC</span>
            </div>
          </div>

          {/* Forwarded Tainted Output */}
          <div
            onMouseEnter={() => setActiveNode('forward')}
            onMouseLeave={() => setActiveNode(null)}
            style={{
              padding: '0.5rem 0.65rem',
              borderRadius: 'var(--radius-sm)',
              background: activeNode === 'forward' ? 'rgba(239, 68, 68, 0.18)' : 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${activeNode === 'forward' ? 'var(--crimson)' : 'rgba(239, 68, 68, 0.35)'}`,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ fontSize: '0.62rem', color: 'var(--crimson)', fontWeight: 700 }}>
              FORWARD TAINT
            </div>
            <div style={{ fontSize: '0.82rem', fontWeight: 800, color: '#ffffff', fontFamily: 'monospace' }}>
              {forwardBtc} <span style={{ fontSize: '0.68rem', color: 'var(--btc-orange)' }}>BTC</span>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Tooltip Context */}
      <div
        style={{
          marginTop: '0.85rem',
          padding: '0.45rem 0.75rem',
          borderRadius: 'var(--radius-sm)',
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          fontSize: '0.72rem',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          {activeNode === 'input' && 'Source UTXO: Identified as co-spent entity in CIOH cluster cluster_8421.'}
          {activeNode === 'tx' && 'Transaction structure: Standard 2-output peel split with unspent change return.'}
          {activeNode === 'change' && 'Change address recognized via round-value heuristic and one-time script.'}
          {activeNode === 'forward' && 'Forwarded output routed directly toward darknet exchange deposit address.'}
          {!activeNode && 'Hover over UTXO nodes to inspect automated heuristic decomposition rationale.'}
        </span>
        <span style={{ color: 'var(--btc-orange)', fontSize: '0.68rem', fontWeight: 600 }}>
          CONFORMAL CONF: 96.4%
        </span>
      </div>
    </div>
  );
};
