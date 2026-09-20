import React, { useEffect, useRef, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

/**
 * Animated count-up number display.
 * Smoothly interpolates from 0 (or previous value) to the target number on mount/update.
 */
export default function AnimatedNumber({
  value,
  duration = 1.2,
  formatFn = null,
  className = '',
  style = {},
}) {
  const spring = useSpring(0, { duration: duration * 1000, bounce: 0 });
  const display = useTransform(spring, (v) => {
    if (formatFn) return formatFn(v);
    if (Number.isInteger(value)) return Math.round(v).toLocaleString();
    return v.toFixed(2);
  });

  useEffect(() => {
    spring.set(typeof value === 'number' ? value : 0);
  }, [value, spring]);

  return (
    <motion.span className={className} style={style}>
      {display}
    </motion.span>
  );
}
