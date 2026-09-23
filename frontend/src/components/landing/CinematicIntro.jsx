import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChainSentinelLogo } from '../visuals/icons';

/**
 * Custom Coin Face Artwork
 * Original cryptographic coin face vector illustration.
 */
function CustomCoinFace({ size = 120 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ filter: 'drop-shadow(0 10px 25px rgba(0, 0, 0, 0.7))' }}
    >
      <defs>
        <radialGradient id="coinGrad" cx="45%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#fcd34d" />
          <stop offset="45%" stopColor="#f59e0b" />
          <stop offset="85%" stopColor="#b45309" />
          <stop offset="100%" stopColor="#78350f" />
        </radialGradient>
        <linearGradient id="rimGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fef08a" />
          <stop offset="30%" stopColor="#d97706" />
          <stop offset="70%" stopColor="#92400e" />
          <stop offset="100%" stopColor="#451a03" />
        </linearGradient>
        <radialGradient id="innerGlow" cx="50%" cy="50%" r="50%">
          <stop offset="70%" stopColor="#f59e0b" stopOpacity="0" />
          <stop offset="100%" stopColor="#b45309" stopOpacity="0.4" />
        </radialGradient>
      </defs>

      {/* Outer Coin Edge / Bevel */}
      <circle cx="60" cy="60" r="57" fill="url(#rimGrad)" stroke="#fef08a" strokeWidth="1.5" />
      <circle cx="60" cy="60" r="52" fill="url(#coinGrad)" />

      {/* Milled Ridge Pattern / Cryptographic Hash Ring */}
      <circle
        cx="60"
        cy="60"
        r="47"
        stroke="#fef08a"
        strokeWidth="1.2"
        strokeDasharray="2 3"
        strokeOpacity="0.6"
      />

      <circle cx="60" cy="60" r="44" fill="url(#innerGlow)" stroke="#92400e" strokeWidth="0.8" />

      {/* Original Stylized Forensic Ledger Glyph (Not a standard trademark logo) */}
      <g transform="translate(60, 60)">
        {/* Dual Vertical Forensic Stems */}
        <line x1="-7" y1="-30" x2="-7" y2="30" stroke="#fef08a" strokeWidth="3" strokeLinecap="round" />
        <line x1="3" y1="-30" x2="3" y2="30" stroke="#fef08a" strokeWidth="3" strokeLinecap="round" />

        {/* Central Interlocking Node Curves */}
        <path
          d="M -16 -21 H 4 C 13 -21 19 -14 19 -5 C 19 3 13 8 4 8 H -16 M -16 8 H 6 C 16 8 22 14 22 22 C 22 30 15 35 4 35 H -16"
          fill="none"
          stroke="#fffbeb"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Node Verification Points */}
        <circle cx="4" cy="-5" r="2.5" fill="#fef08a" />
        <circle cx="6" cy="22" r="2.5" fill="#fef08a" />
        <circle cx="-16" cy="-21" r="2" fill="#fef08a" />
        <circle cx="-16" cy="8" r="2" fill="#fef08a" />
        <circle cx="-16" cy="35" r="2" fill="#fef08a" />
      </g>
    </svg>
  );
}

/**
 * CinematicIntro
 * Controls Phase 1 (physics bounce), Phase 2 (network expansion & anomaly targeting),
 * and Phase 3 (morph handoff).
 */
export default function CinematicIntro({ onSequenceComplete, isSkipped = false }) {
  const [step, setStep] = useState(1); // 1: bounce, 2: network reveal, 3: anomaly highlight, 4: targeting reticle, 5: logo reveal, 6: handoff

  useEffect(() => {
    if (isSkipped) {
      onSequenceComplete();
      return;
    }

    // Step 1: Coin bounce (0 -> 2.4s)
    const t1 = setTimeout(() => setStep(2), 2400);

    // Step 2: Coin transforms into node, network expands (2.4s -> 4.2s)
    const t2 = setTimeout(() => setStep(3), 4200);

    // Step 3: Anomaly detection alert pulse (4.2s -> 5.6s)
    const t3 = setTimeout(() => setStep(4), 5600);

    // Step 4: Reticle targeting lock & graph fade (5.6s -> 6.8s)
    const t4 = setTimeout(() => setStep(5), 6800);

    // Step 5: Logo centered reveal (6.8s -> 7.8s)
    const t5 = setTimeout(() => setStep(6), 7800);

    // Step 6: Handoff to CommandBar position & finish (7.8s -> 8.6s)
    const t6 = setTimeout(() => {
      onSequenceComplete();
    }, 8600);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      clearTimeout(t5);
      clearTimeout(t6);
    };
  }, [isSkipped, onSequenceComplete]);

  // Graph nodes layout
  const nodes = [
    { id: 'origin', x: 400, y: 300, label: 'Wallet-Alpha', size: 14, isOrigin: true },
    { id: 'n1', x: 260, y: 220, label: 'Peer 1', size: 10 },
    { id: 'n2', x: 540, y: 210, label: 'Peer 2', size: 10 },
    { id: 'n3', x: 220, y: 380, label: 'Mixer Inflow', size: 11 },
    { id: 'n4', x: 380, y: 450, label: 'Splitter', size: 10 },
    { id: 'illicit', x: 570, y: 390, label: 'Illicit Cluster', size: 15, isAnomaly: true },
    { id: 'n6', x: 670, y: 470, label: 'Cashout', size: 12, isAnomaly: true },
  ];

  const edges = [
    { from: 'origin', to: 'n1' },
    { from: 'origin', to: 'n2' },
    { from: 'origin', to: 'n3' },
    { from: 'n1', to: 'n3' },
    { from: 'origin', to: 'n4' },
    { from: 'origin', to: 'illicit', isAnomaly: true },
    { from: 'illicit', to: 'n6', isAnomaly: true },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: '#0a0806',
        zIndex: 99990,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Background Subtle Forensic Grid */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle at 50% 50%, rgba(247, 147, 26, 0.04) 0%, transparent 60%), linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)',
          backgroundSize: '100% 100%, 40px 40px, 40px 40px',
          opacity: step >= 2 ? 0.9 : 0.2,
          transition: 'opacity 1s ease',
        }}
      />

      {/* PHASE 1: Dropped Coin Physics Bounce */}
      <AnimatePresence>
        {step === 1 && (
          <div
            style={{
              position: 'relative',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Coin Thud Shadow / Shockwave Ring */}
            <motion.div
              style={{
                position: 'absolute',
                bottom: -20,
                width: 140,
                height: 28,
                borderRadius: '50%',
                background: 'radial-gradient(ellipse at center, rgba(247, 147, 26, 0.5) 0%, rgba(247, 147, 26, 0) 75%)',
                filter: 'blur(4px)',
              }}
              animate={{
                scale: [0, 1.6, 0.2, 1.2, 0.5, 1.0, 0.8, 1.0],
                opacity: [0, 0.9, 0.1, 0.6, 0.2, 0.4, 0.2, 0.3],
              }}
              transition={{
                duration: 2.3,
                times: [0, 0.35, 0.45, 0.68, 0.76, 0.88, 0.94, 1.0],
              }}
            />

            {/* Bouncing Coin */}
            <motion.div
              initial={{ y: -500, scale: 0.9, opacity: 0 }}
              animate={{
                y: [-500, 0, -170, 0, -55, 0, -15, 0],
                opacity: [0, 1, 1, 1, 1, 1, 1, 1],
                scale: [0.95, 1.06, 0.98, 1.03, 0.99, 1.01, 1, 1],
              }}
              transition={{
                duration: 2.3,
                times: [0, 0.35, 0.55, 0.7, 0.82, 0.9, 0.96, 1.0],
                ease: [
                  'easeIn',
                  'easeOut',
                  'easeIn',
                  'easeOut',
                  'easeIn',
                  'easeOut',
                  'easeIn',
                ],
              }}
            >
              <CustomCoinFace size={130} />
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* PHASE 2: Network Emergence & Anomaly Storyboard (Steps 2-4) */}
      <AnimatePresence>
        {step >= 2 && step <= 4 && (
          <motion.div
            initial={{ opacity: 0, scale: 1.4 }}
            animate={{
              opacity: step === 4 ? [1, 1, 0] : 1,
              scale: step >= 3 ? 0.92 : 1.0,
            }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.8, ease: 'easeInOut' }}
            style={{
              position: 'relative',
              width: '800px',
              height: '600px',
              maxWidth: '95vw',
              maxHeight: '90vh',
            }}
          >
            <svg
              viewBox="0 0 800 600"
              style={{ width: '100%', height: '100%', overflow: 'visible' }}
            >
              <defs>
                {/* Illicit Edge Gradient */}
                <linearGradient id="illicitEdgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#f7931a" />
                  <stop offset="100%" stopColor="#ef4444" />
                </linearGradient>
              </defs>

              {/* Connecting Transaction Edges */}
              {edges.map((e, idx) => {
                const source = nodes.find((n) => n.id === e.from);
                const target = nodes.find((n) => n.id === e.to);
                if (!source || !target) return null;

                const isAnomalyEdge = e.isAnomaly && step >= 3;

                return (
                  <g key={`${e.from}-${e.to}`}>
                    {/* Background Static Track */}
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={isAnomalyEdge ? 'rgba(239, 68, 68, 0.4)' : 'rgba(255, 255, 255, 0.12)'}
                      strokeWidth={isAnomalyEdge ? 2.5 : 1.5}
                    />

                    {/* Animated Edge Flow (Fund Movement) */}
                    <motion.line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={isAnomalyEdge ? '#ef4444' : 'rgba(247, 147, 26, 0.65)'}
                      strokeWidth={isAnomalyEdge ? 3 : 1.8}
                      strokeDasharray="6 6"
                      initial={{ strokeDashoffset: 0 }}
                      animate={{ strokeDashoffset: -36 }}
                      transition={{
                        repeat: Infinity,
                        duration: 1.2,
                        ease: 'linear',
                        delay: idx * 0.15,
                      }}
                    />
                  </g>
                );
              })}

              {/* Transaction Graph Nodes */}
              {nodes.map((node) => {
                const isAnomaly = node.isAnomaly && step >= 3;

                return (
                  <g key={node.id}>
                    {/* Anomaly Pulse Wave */}
                    {isAnomaly && (
                      <motion.circle
                        cx={node.x}
                        cy={node.y}
                        r={node.size * 2.2}
                        fill="none"
                        stroke="#ef4444"
                        strokeWidth="1.5"
                        initial={{ scale: 0.8, opacity: 0.8 }}
                        animate={{ scale: [1, 2.2, 1], opacity: [0.8, 0, 0.8] }}
                        transition={{ repeat: Infinity, duration: 1.5, ease: 'easeOut' }}
                      />
                    )}

                    {/* Node Core */}
                    <motion.circle
                      cx={node.x}
                      cy={node.y}
                      r={node.size}
                      fill={
                        isAnomaly
                          ? '#ef4444'
                          : node.isOrigin
                          ? '#f7931a'
                          : '#261e16'
                      }
                      stroke={
                        isAnomaly
                          ? '#fecaca'
                          : node.isOrigin
                          ? '#fef08a'
                          : 'rgba(255, 255, 255, 0.3)'
                      }
                      strokeWidth={node.isOrigin ? 2.5 : 1.5}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 0.4, delay: node.isOrigin ? 0 : 0.2 }}
                    />

                    {/* Node Mini Label */}
                    <text
                      x={node.x}
                      y={node.y + node.size + 14}
                      textAnchor="middle"
                      fill={isAnomaly ? '#fca5a5' : 'rgba(255, 255, 255, 0.6)'}
                      fontSize="10"
                      fontFamily="JetBrains Mono, monospace"
                      fontWeight={node.isOrigin || isAnomaly ? '700' : '400'}
                    >
                      {node.label}
                    </text>
                  </g>
                );
              })}

              {/* Targeting Reticle around Anomaly Cluster (Step 4) */}
              {step >= 3 && (
                <g>
                  {/* Forensic Targeting Ring */}
                  <motion.g
                    initial={{ opacity: 0, scale: 1.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                    transform="translate(570, 390)"
                  >
                    <circle
                      r="42"
                      fill="none"
                      stroke="#ef4444"
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                    />
                    <line x1="-50" y1="0" x2="-35" y2="0" stroke="#ef4444" strokeWidth="2" />
                    <line x1="35" y1="0" x2="50" y2="0" stroke="#ef4444" strokeWidth="2" />
                    <line x1="0" y1="-50" x2="0" y2="-35" stroke="#ef4444" strokeWidth="2" />
                    <line x1="0" y1="35" x2="0" y2="50" stroke="#ef4444" strokeWidth="2" />
                  </motion.g>

                  {/* Illicit Flow Detection Label */}
                  <motion.g
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.2 }}
                  >
                    <rect
                      x="610"
                      y="340"
                      width="155"
                      height="26"
                      rx="4"
                      fill="rgba(239, 68, 68, 0.15)"
                      stroke="#ef4444"
                      strokeWidth="1"
                    />
                    <text
                      x="687"
                      y="357"
                      textAnchor="middle"
                      fill="#ef4444"
                      fontSize="11"
                      fontFamily="system-ui, sans-serif"
                      fontWeight="700"
                      letterSpacing="0.05em"
                    >
                      ILLICIT FLOW DETECTED
                    </text>
                  </motion.g>
                </g>
              )}
            </svg>
          </motion.div>
        )}
      </AnimatePresence>

      {/* PHASE 3: Logo Reveal & Handoff Morph (Steps 5 & 6) */}
      <AnimatePresence>
        {step >= 5 && (
          <motion.div
            style={{
              position: 'fixed',
              top: step === 6 ? '10px' : '50%',
              left: step === 6 ? '20px' : '50%',
              x: step === 6 ? 0 : '-50%',
              y: step === 6 ? 0 : '-50%',
              display: 'flex',
              alignItems: 'center',
              gap: step === 6 ? '0.5rem' : '1rem',
              zIndex: 99999,
            }}
            transition={{
              type: 'spring',
              stiffness: 280,
              damping: 26,
              duration: 0.8,
            }}
          >
            <motion.div
              layoutId="chainsentinel-brand-logo"
              className="brand-logo"
              style={{
                width: step === 6 ? '32px' : '64px',
                height: step === 6 ? '32px' : '64px',
              }}
              transition={{ duration: 0.6 }}
            >
              <ChainSentinelLogo size={step === 6 ? 22 : 44} />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              style={{ display: 'flex', flexDirection: 'column' }}
            >
              <span
                style={{
                  fontSize: step === 6 ? '0.95rem' : '2.2rem',
                  fontWeight: 800,
                  color: 'var(--text-emphasis)',
                  letterSpacing: '-0.02em',
                }}
              >
                ChainSentinel
              </span>
              {step < 6 && (
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--btc-orange)',
                    fontWeight: 700,
                    letterSpacing: '0.15em',
                    textTransform: 'uppercase',
                  }}
                >
                  Autonomous Bitcoin Forensic Workspace
                </span>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
