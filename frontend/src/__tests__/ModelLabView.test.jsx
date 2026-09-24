import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ModelLabView from '../components/ModelLabView';
import { ToastProvider } from '../components/shared/Toast';

vi.mock('../api', () => ({
  api: {
    getModelLab: vi.fn(() => Promise.resolve({
      supervised_metrics: {
        ['accuracy']: 0.942,
        ['f1_macro']: 0.915,
      },
      conformal: {
        coverage: 0.908,
      },
      holdout_experiment: {
        flagged_as_anomalous_ratio: 0.887,
        ['legitimate_anomaly_mean']: 0.21,
        ['holdout_anomaly_mean']: 0.78,
        ['anomaly_separation_delta']: 0.57,
      },
      feature_importances: [
        { feature: 'peel_chain_ratio', importance: 0.28 },
        { feature: 'fan_out_degree', importance: 0.22 },
        { feature: 'velocity_sats_per_sec', importance: 0.15 },
      ],
    })),
    trainModels: vi.fn(() => Promise.resolve({
      status: 'ok',
      message: 'Models trained successfully',
    })),
  },
}));


// Mock charts so they don't break in jsdom
vi.mock('../components/charts/FeatureImportanceChart', () => ({
  default: ({ features }) => (
    <div data-testid="feature-importance-chart">
      Features: {features?.length ?? 0}
    </div>
  ),
}));

vi.mock('../components/charts/AnomalyDistribution', () => ({
  default: ({ separationDelta }) => (
    <div data-testid="anomaly-distribution-chart">
      Delta: {separationDelta}
    </div>
  ),
}));

const renderWithToast = (ui) => render(<ToastProvider>{ui}</ToastProvider>);

describe('ModelLabView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders intelligence laboratory header and KPI metrics', async () => {
    renderWithToast(<ModelLabView />);

    expect(await screen.findByText(/AI\/ML Intelligence Laboratory/i)).toBeInTheDocument();
    expect(screen.getByText(/Typology Accuracy/i)).toBeInTheDocument();
    expect(screen.getByText(/F1 Macro Score/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Conformal Coverage/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Unseen Anomaly Catch/i)).toBeInTheDocument();
    expect(screen.getByTestId('feature-importance-chart')).toBeInTheDocument();
    expect(screen.getByTestId('anomaly-distribution-chart')).toBeInTheDocument();
  });

  it('calls api.getModelLab when Refresh Lab button is clicked', async () => {
    const { api } = await import('../api');
    renderWithToast(<ModelLabView />);

    expect(await screen.findByText(/AI\/ML Intelligence Laboratory/i)).toBeInTheDocument();
    const refreshBtn = screen.getByRole('button', { name: /Refresh Lab/i });
    fireEvent.click(refreshBtn);

    expect(api.getModelLab).toHaveBeenCalled();
  });

  it('calls api.trainModels when Retrain All Models button is clicked', async () => {
    const { api } = await import('../api');
    renderWithToast(<ModelLabView />);

    expect(await screen.findByText(/AI\/ML Intelligence Laboratory/i)).toBeInTheDocument();
    const retrainBtn = screen.getByRole('button', { name: /Retrain All Models/i });
    fireEvent.click(retrainBtn);

    expect(api.trainModels).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByText(/Retrain All Models/i)).toBeInTheDocument();
    });
  });
});
