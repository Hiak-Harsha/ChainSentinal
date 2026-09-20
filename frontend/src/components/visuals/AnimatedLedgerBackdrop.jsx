import React, { useEffect, useRef } from 'react';

/**
 * AnimatedLedgerBackdrop
 * Ultra-faint ambient Bitcoin ledger matrix stream.
 * Renders drifting hexadecimal hashes, block heights, and satoshi amounts at ~2-3% opacity.
 * Self-throttling, GPU-friendly, respects prefers-reduced-motion.
 */
export const AnimatedLedgerBackdrop = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      initColumns();
    };
    window.addEventListener('resize', handleResize);

    const chars = '0123456789abcdefABCDEF';
    const sampleSnippets = [
      '000000000019d6689c085ae165831e934ff763ae',
      'tx:4a5e1e4baab89f3a32518a88c31bc87f618f7667',
      'blk:#883419',
      'sats:42081920',
      'input:utxo:c98a',
      'OP_CHECKSIG',
      'OP_DUP_HASH160',
      'diff:84.2T',
      'coinjoin:entropy:0.94',
      'peel:drop:0.041BTC',
      'cioh:cluster:e4f7',
    ];

    const fontSize = 12;
    let columns = Math.floor(width / 160);
    if (columns < 4) columns = 4;
    let drops = [];

    const initColumns = () => {
      columns = Math.floor(width / 160);
      if (columns < 4) columns = 4;
      drops = [];
      for (let i = 0; i < columns; i++) {
        drops.push({
          x: i * 160 + 20,
          y: Math.random() * height,
          speed: 0.35 + Math.random() * 0.45,
          snippetIndex: Math.floor(Math.random() * sampleSnippets.length),
          text: sampleSnippets[Math.floor(Math.random() * sampleSnippets.length)],
        });
      }
    };

    initColumns();

    if (prefersReducedMotion) {
      // Draw static ambient ledger grid once without continuous loop
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = 'rgba(0, 242, 254, 0.025)';
      ctx.font = `${fontSize}px "JetBrains Mono", monospace`;
      drops.forEach((drop) => {
        ctx.fillText(drop.text, drop.x, drop.y);
      });
      return () => {
        window.removeEventListener('resize', handleResize);
      };
    }

    let lastTime = 0;
    const fpsInterval = 1000 / 30; // Cap at 30fps for minimal CPU overhead

    const render = (currentTime) => {
      animationFrameId = requestAnimationFrame(render);

      const elapsed = currentTime - lastTime;
      if (elapsed < fpsInterval) return;
      lastTime = currentTime - (elapsed % fpsInterval);

      // Semi-transparent clear to leave a very subtle fade trail
      ctx.fillStyle = 'rgba(6, 9, 17, 0.2)';
      ctx.fillRect(0, 0, width, height);

      ctx.font = `${fontSize}px "JetBrains Mono", monospace`;

      drops.forEach((drop) => {
        // Subtle cyan or btc-orange tint with extremely low opacity
        const isBtcSnippet = drop.text.includes('BTC') || drop.text.includes('sats') || drop.text.includes('coinjoin');
        ctx.fillStyle = isBtcSnippet ? 'rgba(247, 147, 26, 0.035)' : 'rgba(0, 242, 254, 0.028)';
        ctx.fillText(drop.text, drop.x, drop.y);

        drop.y += drop.speed * 8;

        if (drop.y > height + 30) {
          drop.y = -20;
          drop.x = Math.random() * width;
          drop.snippetIndex = (drop.snippetIndex + 1) % sampleSnippets.length;
          // Mutate text slightly with random hex chars
          const base = sampleSnippets[drop.snippetIndex];
          const randHex = chars.charAt(Math.floor(Math.random() * chars.length));
          drop.text = base.slice(0, -1) + randHex;
        }
      });
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="ledger-backdrop-layer" aria-hidden="true">
      <canvas ref={canvasRef} style={{ display: 'block', width: '100%', height: '100%' }} />
    </div>
  );
};
