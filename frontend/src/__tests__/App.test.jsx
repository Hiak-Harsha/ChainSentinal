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
    getAlertTimeseries: vi.fn().mockResolvedValue([{ bucket: 'T-1', count: 2 }, { bucket: 'Now', count: 4 }]),
    getSimilarEntities: vi.fn().mockResolvedValue([]),
    submitAlertFeedback: vi.fn().mockResolvedValue({}),
    startJob: vi.fn().mockResolvedValue({ job_id: 'mock_job' }),
    getJobStatus: vi.fn().mockResolvedValue({ status: 'completed' }),
  },
}));

// Mock framer-motion to avoid animation issues in jsdom
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, layoutId, whileHover, whileTap, initial, animate, exit, transition, ...props }) => <div {...props}>{children}</div>,
    span: ({ children, layoutId, whileHover, whileTap, initial, animate, exit, transition, ...props }) => <span {...props}>{children}</span>,
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

  it('renders the CommandBar branding, mode switcher, and workspace shell', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('ChainSentinel')).toBeInTheDocument();
    });

    expect(screen.getByText('NTRO SIH-2026')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Search entities, alerts, addresses/i)).toBeInTheDocument();

    // CommandBar modes
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Network')).toBeInTheDocument();
    expect(screen.getByText('Alerts')).toBeInTheDocument();
    expect(screen.getByText('Taint')).toBeInTheDocument();
    expect(screen.getByText('Models')).toBeInTheDocument();
    expect(screen.getByText('Ingest')).toBeInTheDocument();

    // Context Rail & Inspector Panel
    expect(screen.getByText('Recent Entities')).toBeInTheDocument();
    expect(screen.getByText('Saved Filters')).toBeInTheDocument();
    expect(screen.getByText('No Selection')).toBeInTheDocument();
  });

  it('switches modes when CommandBar mode buttons are clicked', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('ChainSentinel')).toBeInTheDocument();
    });

    // Switch to Alerts mode
    const alertsBtn = screen.getByRole('button', { name: /Alerts/i });
    fireEvent.click(alertsBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Alert/i).length).toBeGreaterThan(0);
    });

    // Switch to Taint mode
    const taintBtn = screen.getByRole('button', { name: /Taint/i });
    fireEvent.click(taintBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Taint/i).length).toBeGreaterThan(0);
    });

    // Switch to Models mode
    const modelsBtn = screen.getByRole('button', { name: /Models/i });
    fireEvent.click(modelsBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Model/i).length).toBeGreaterThan(0);
    });
  });
});
