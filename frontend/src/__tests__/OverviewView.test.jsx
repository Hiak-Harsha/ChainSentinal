import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import OverviewView from '../components/OverviewView';
import { ToastProvider } from '../components/shared/Toast';

function renderWithToast(ui) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

describe('OverviewView Component', () => {
  const mockMetrics = {
    total_entities: 142,
    total_edges: 388,
    total_transactions: 250,
    total_addresses: 620,
    total_quarantined: 3,
    total_volume_btc: 1842.5,
    total_volume_sat: 184250000000,
    mean_risk_score: 0.45,
    high_risk_alerts: 4,
    recent_jobs: [
      { job_id: 'job_001', format: 'csv', status: 'completed', valid_rows: 18, quarantined_rows: 2 },
    ],
    recent_cases: [
      { case_id: 'case_001', title: 'Suspicious Ransomware Flow', target_id: 'bc1qtest123', status: 'INVESTIGATING' },
    ],
  };

  const mockAlerts = [
    {
      alert_id: 'alt_001',
      entity_id: 'ENT_DARKNET_01',
      risk_score: 0.85,
      priority: 0.85,
      status: 'NEW',
      confidence: { grade: 'A' },
    },
  ];

  const mockHealth = { status: 'ok' };

  it('renders threat center header, KPIs, and online status badge', () => {
    renderWithToast(
      <OverviewView
        metrics={mockMetrics}
        alerts={mockAlerts}
        health={mockHealth}
      />
    );

    expect(screen.getByText(/Forensic Operations Threat Center/i)).toBeInTheDocument();
    expect(screen.getByText(/BACKEND ONLINE/i)).toBeInTheDocument();
    expect(screen.getByText(/RESOLVED ENTITIES/i)).toBeInTheDocument();
    expect(screen.getByText(/1842.5 BTC/i)).toBeInTheDocument();
  });

  it('calls onTriggerDetect when Run Detection Engine button is clicked', () => {
    const handleDetect = vi.fn();
    renderWithToast(
      <OverviewView
        metrics={mockMetrics}
        alerts={mockAlerts}
        health={mockHealth}
        onTriggerDetect={handleDetect}
      />
    );

    const detectBtn = screen.getByRole('button', { name: /Run Detection Engine/i });
    fireEvent.click(detectBtn);
    expect(handleDetect).toHaveBeenCalled();
  });

  it('navigates to network tab when Explore Network button is clicked', () => {
    const handleSwitch = vi.fn();
    renderWithToast(
      <OverviewView
        metrics={mockMetrics}
        alerts={mockAlerts}
        health={mockHealth}
        onSwitchTab={handleSwitch}
      />
    );

    const exploreBtn = screen.getByRole('button', { name: /Explore Network/i });
    fireEvent.click(exploreBtn);
    expect(handleSwitch).toHaveBeenCalledWith('graph');
  });

  it('calls onSelectAlert when an alert row action is clicked', () => {
    const handleSelectAlert = vi.fn();
    renderWithToast(
      <OverviewView
        metrics={mockMetrics}
        alerts={mockAlerts}
        health={mockHealth}
        onSelectAlert={handleSelectAlert}
      />
    );

    const investigateBtn = screen.getByRole('button', { name: /Investigate/i });
    fireEvent.click(investigateBtn);
    expect(handleSelectAlert).toHaveBeenCalledWith(mockAlerts[0]);
  });
});
