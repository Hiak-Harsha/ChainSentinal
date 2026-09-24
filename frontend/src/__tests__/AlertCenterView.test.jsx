import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AlertCenterView from '../components/AlertCenterView';
import { ToastProvider } from '../components/shared/Toast';

vi.mock('../api', () => ({
  api: {
    updateAlertStatus: vi.fn(),
  },
}));

const renderWithToast = (ui) => render(<ToastProvider>{ui}</ToastProvider>);

describe('AlertCenterView Component (List-Only Overlay)', () => {
  const mockAlerts = [
    {
      alert_id: 'ALT-101',
      entity_id: 'ENT-ALPHA',
      risk_score: 0.92,
      priority: 0.92,
      status: 'NEW',
      typology: 'T2_COINJOIN',
      typologies: [{ name: 'CoinJoin Mixer', score: 0.92, strength: 0.92 }],
      confidence: { grade: 'A' },
      attribution: { ip: '198.51.100.1', country: 'US', asn: 'AS13335' },
    },
    {
      alert_id: 'ALT-102',
      entity_id: 'ENT-BETA',
      risk_score: 0.45,
      priority: 0.45,
      status: 'RESOLVED',
      typology: 'T8_DUSTING',
      typologies: [{ name: 'Dusting Attack', score: 0.45, strength: 0.45 }],
      confidence: { grade: 'C' },
      attribution: { ip: '203.0.113.5', country: 'DE', asn: 'AS24940' },
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders alerts in the queue table with IDs and entity targets', () => {
    renderWithToast(<AlertCenterView alerts={mockAlerts} />);

    expect(screen.getByText('ALT-101')).toBeInTheDocument();
    expect(screen.getByText('ALT-102')).toBeInTheDocument();
    expect(screen.getByText('ENT-ALPHA')).toBeInTheDocument();
    expect(screen.getByText('ENT-BETA')).toBeInTheDocument();
  });

  it('filters alerts by status select dropdown', () => {
    renderWithToast(<AlertCenterView alerts={mockAlerts} />);

    const selects = screen.getAllByRole('combobox');
    const statusSelect = selects[0]; // first select is status
    fireEvent.change(statusSelect, { target: { value: 'NEW' } });

    expect(screen.getByText('ALT-101')).toBeInTheDocument();
    expect(screen.queryByText('ALT-102')).not.toBeInTheDocument();
  });

  it('filters alerts by grade select dropdown', () => {
    renderWithToast(<AlertCenterView alerts={mockAlerts} />);

    const selects = screen.getAllByRole('combobox');
    const gradeSelect = selects[1]; // second select is grade
    fireEvent.change(gradeSelect, { target: { value: 'A' } });

    expect(screen.getByText('ALT-101')).toBeInTheDocument();
    expect(screen.queryByText('ALT-102')).not.toBeInTheDocument();
  });

  it('filters alerts by minimum risk score', () => {
    renderWithToast(<AlertCenterView alerts={mockAlerts} />);

    const selects = screen.getAllByRole('combobox');
    const riskSelect = selects[2]; // third select is min risk
    fireEvent.change(riskSelect, { target: { value: '0.7' } });

    expect(screen.getByText('ALT-101')).toBeInTheDocument();
    expect(screen.queryByText('ALT-102')).not.toBeInTheDocument();
  });

  it('triggers onSelectAlert when Deep Dive button is clicked', () => {
    const onSelectAlert = vi.fn();
    renderWithToast(<AlertCenterView alerts={mockAlerts} onSelectAlert={onSelectAlert} />);

    const deepDiveButtons = screen.getAllByRole('button', { name: /Deep Dive/i });
    expect(deepDiveButtons.length).toBe(2);
    fireEvent.click(deepDiveButtons[0]);

    expect(onSelectAlert).toHaveBeenCalledWith(expect.objectContaining({ alert_id: 'ALT-101' }));
  });

  it('triggers onSelectAlert when table row is clicked', () => {
    const onSelectAlert = vi.fn();
    renderWithToast(<AlertCenterView alerts={mockAlerts} onSelectAlert={onSelectAlert} />);

    const typologyCell = screen.getByText('Dusting Attack');
    fireEvent.click(typologyCell);

    expect(onSelectAlert).toHaveBeenCalledWith(expect.objectContaining({ alert_id: 'ALT-102' }));
  });
});
