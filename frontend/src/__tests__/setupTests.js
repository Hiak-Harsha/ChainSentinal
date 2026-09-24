import '@testing-library/jest-dom';
import React from 'react';
import { vi } from 'vitest';

// Global comprehensive framer-motion mock without JSX syntax
vi.mock('framer-motion', () => ({
  motion: new Proxy({}, {
    get: (target, prop) => {
      const Comp = React.forwardRef(({ children, ...props }, ref) =>
        React.createElement(prop, { ref, ...props }, children)
      );
      Comp.displayName = `motion.${prop}`;
      return Comp;
    },
  }),
  AnimatePresence: ({ children }) => React.createElement(React.Fragment, null, children),
  useSpring: (initial) => ({
    get: () => (typeof initial === 'number' ? initial : 0),
    set: vi.fn(),
    onChange: vi.fn(),
  }),
  useTransform: (val, fn) => {
    const raw = typeof val === 'object' && val?.get ? val.get() : val;
    return typeof fn === 'function' ? fn(raw) : raw;
  },
  useMotionValue: (initial) => ({
    get: () => initial,
    set: vi.fn(),
  }),
  useReducedMotion: () => false,
}));
