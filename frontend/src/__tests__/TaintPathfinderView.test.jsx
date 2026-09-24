import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TaintPathfinderView from '../components/TaintPathfinderView';
import { ToastProvider } from '../components/shared/Toast';

vi.mock('../api', () => ({
  api: {
    runTrace: vi.fn((params) => Promise.resolve({
      target: params.target,
      direction: params.direction,
      decay_model: params.decay_model,
      max_hops: params.max_hops,
      total_dispersion: 50000000,
      hops: [
        {
          hop_index: 1,
          entity_id: 'ENT_TARGET_HOP1',
          entity_type: 'MIXER',
          taint_score: 0.85,
          satoshis: 42500000,
        },
      ],
      nodes: [
        { id: params.target, type: 'EXCHANGE' },
        { id: 'ENT_TARGET_HOP1', type: 'MIXER' },
      ],
      edges: [
        { source: params.target, target: 'ENT_TARGET_HOP1', value: 42500000 },
      ],
    })),
    computePath: vi.fn((params) => Promise.resolve({
      source: params.source,
      target: params.target,
      strategy: params.strategy,
      found: true,
      hop_count: 2,
      path: ['ENT_SRC', 'ENT_MID', 'ENT_DST'],
      edges: [],
    })),
  },
}));

vi.mock('../components/process/TaintDecayVisualizer', () => ({
  default: () => <div data-testid="taint-decay-visualizer" />,
}));

const renderWithToast = (ui) => render(<ToastProvider>{ui}</ToastProvider>);

describe('TaintPathfinderView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders taint dispersion simulator with default controls', () => {
    renderWithToast(<TaintPathfinderView prefilledTarget="ENT_SRC_123" />);

    expect(screen.getByText(/Dynamic Taint Dispersion Simulator/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue('ENT_SRC_123')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Execute Taint Trace/i })).toBeInTheDocument();
  });

  it('calls api.runTrace with correct arguments and invokes onTraceCompleted', async () => {
    const { api } = await import('../api');
    const onTraceCompleted = vi.fn();
    renderWithToast(<TaintPathfinderView prefilledTarget="ENT_SRC_123" onTraceCompleted={onTraceCompleted} />);

    const runBtn = screen.getByRole('button', { name: /Execute Taint Trace/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(api.runTrace).toHaveBeenCalledWith(expect.objectContaining({
        target: 'ENT_SRC_123',
        direction: 'forward',
        decay_model: 'proportional',
      }));
    });

    expect(onTraceCompleted).toHaveBeenCalled();
  });

  it('switches subtabs to pathfinder and computes shortest/widest path', async () => {
    const { api } = await import('../api');
    const { container } = renderWithToast(<TaintPathfinderView />);

    const pathTabBtn = screen.getByRole('button', { name: /Forensic Route Pathfinder/i });
    fireEvent.click(pathTabBtn);

    expect(screen.getByText(/Forensic Corridor & Bottleneck Pathfinder/i)).toBeInTheDocument();

    fireEvent.change(container.querySelector('#pathfinder-source-input'), { target: { value: 'ENT_SRC_999' } });
    fireEvent.change(container.querySelector('#pathfinder-target-input'), { target: { value: 'ENT_DST_999' } });
    fireEvent.click(container.querySelector('#btn-calculate-path'));

    await waitFor(() => {
      expect(api.computePath).toHaveBeenCalledWith(expect.objectContaining({
        source: 'ENT_SRC_999',
        target: 'ENT_DST_999',
        strategy: 'highest_volume',
      }));
    });
  });
});
