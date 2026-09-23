import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FastForward } from 'lucide-react';
import CinematicIntro from './CinematicIntro';

/**
 * LandingSequence
 * Orchestrates the full cinematic intro flow:
 *   - 'cinematic' phase (coin bounce -> network flow -> anomaly targeting -> logo reveal)
 *   - 'transition' phase (logo morph to CommandBar)
 *   - visible "Skip Intro" button from frame 1
 *   - handles keyboard and click skip
 *   - respects prefers-reduced-motion
 */
export default function LandingSequence({ onComplete }) {
  const [skipped, setSkipped] = useState(false);

  const handleSkip = useCallback(() => {
    setSkipped(true);
    if (onComplete) onComplete();
  }, [onComplete]);

  // Accessibility: respects prefers-reduced-motion
  useEffect(() => {
    const mediaQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (mediaQuery && mediaQuery.matches) {
      handleSkip();
    }
  }, [handleSkip]);

  // Global skip listener: any keypress or click immediately advances into workspace
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't intercept if user is typing in an input (not applicable in intro, but good practice)
      handleSkip();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSkip]);

  return (
    <div
      id="landing-sequence-container"
      onClick={handleSkip}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: '#0a0806',
        zIndex: 99999,
        cursor: 'pointer',
      }}
    >
      {/* Frame 1 Visible Skip Intro Button */}
      <button
        id="btn-skip-intro"
        onClick={(e) => {
          e.stopPropagation();
          handleSkip();
        }}
        aria-label="Skip Introduction"
        style={{
          position: 'fixed',
          top: 'var(--space-4)',
          right: 'var(--space-4)',
          zIndex: 100005,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: '0.45rem 0.85rem',
          borderRadius: 'var(--radius-full)',
          background: 'rgba(24, 18, 12, 0.75)',
          backdropFilter: 'blur(8px)',
          border: '1px solid var(--border-neutral)',
          color: 'var(--text-main)',
          fontSize: '0.78rem',
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--border-neutral-hover)';
          e.currentTarget.style.color = 'var(--text-emphasis)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--border-neutral)';
          e.currentTarget.style.color = 'var(--text-main)';
        }}
      >
        <span>Skip Intro</span>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '3px', padding: '1px 4px' }}>
          ESC / Click
        </span>
        <FastForward size={13} style={{ color: 'var(--btc-orange)' }} />
      </button>

      {/* Cinematic Animated Sequence */}
      <CinematicIntro onSequenceComplete={handleSkip} isSkipped={skipped} />
    </div>
  );
}
