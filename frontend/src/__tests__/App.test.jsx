import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import { api } from '../api';

// Mock the API client
vi.mock('../api', () => ({
  api: {
    getHealth: vi.fn(),
    getAlerts: vi.fn(),
    getGraphMetrics: vi.fn(),
    getEntities: vi.fn(),
    getAlertSummary: vi.fn(),
    getTaintHistory: vi.fn(),
    getCases: vi.fn().mockResolvedValue([]),
    getTrainingStatus: vi.fn().mockResolvedValue({}),
    getIngestJobs: vi.fn().mockResolvedValue([]),
    getProfiles: vi.fn().mockResolvedValue([]),
    getModelLab: vi.fn().mockResolvedValue({ models: {}, metrics: {} }),
    runDetection: vi.fn().mockResolvedValue([]),
  },
}));

// Mock framer-motion to avoid animation issues in jsdom
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
    span: ({ children, ...props }) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }) => <>{children}</>,
  useSpring: (initial) => ({ set: vi.fn(), get: () => initial }),
  useTransform: (val, fn) => ({ get: () => (typeof fn === 'function' ? fn(0) : 0) }),
}));

// Mock canvas-based backdrop and animated numbers
vi.mock('../components/visuals/AnimatedLedgerBackdrop', () => ({
  AnimatedLedgerBackdrop: () => <div data-testid="ledger-backdrop" />,
}));

vi.mock('../components/shared/AnimatedNumber', () => ({
  default: ({ value, formatFn }) => <span>{formatFn ? formatFn(value) : value}</span>,
  AnimatedNumber: ({ value, formatFn }) => <span>{formatFn ? formatFn(value) : value}</span>,
}));

describe('ChainSentinel App Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getHealth.mockResolvedValue({ status: 'ok', offline: true, uptime_sec: 3600 });
    api.getAlerts.mockResolvedValue([
      { alert_id: 'ALT-1', entity_id: 'ENT-001', typology: 'T2_COINJOIN', risk_score: 0.88, status: 'ACTIVE' },
    ]);
    api.getGraphMetrics.mockResolvedValue({
      total_entities: 2515,
      total_transactions: 1248,
      largest_cluster: 88,
    });
    api.getCases.mockResolvedValue([]);
    api.getTaintHistory.mockResolvedValue([]);
    api.getEntities.mockResolvedValue([]);
  });

  it('renders the header with branding and navigation tabs', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('ChainSentinel')).toBeInTheDocument();
    });

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Alert Center')).toBeInTheDocument();
    expect(screen.getByText('Link Analysis')).toBeInTheDocument();
    expect(screen.getByText('Taint & Pathfinder')).toBeInTheDocument();
    expect(screen.getByText('Model Lab')).toBeInTheDocument();
    expect(screen.getByText('Case Files')).toBeInTheDocument();
    expect(screen.getByText('Ingest Wizard')).toBeInTheDocument();
  });

  it('switches views when navigation tabs are clicked', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('ChainSentinel')).toBeInTheDocument();
    });

    // Switch to Alert Center tab
    const alertsBtn = screen.getByText('Alert Center');
    fireEvent.click(alertsBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Alert/i).length).toBeGreaterThan(0);
    });

    // Switch to Taint & Pathfinder tab
    const taintBtn = screen.getByText('Taint & Pathfinder');
    fireEvent.click(taintBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Taint/i).length).toBeGreaterThan(0);
    });

    // Switch to Model Lab tab
    const modelsBtn = screen.getByText('Model Lab');
    fireEvent.click(modelsBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Model/i).length).toBeGreaterThan(0);
    });
  });
});
