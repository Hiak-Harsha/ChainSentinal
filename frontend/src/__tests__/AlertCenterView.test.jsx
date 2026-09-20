import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AlertCenterView from '../components/AlertCenterView';
import { ToastProvider } from '../components/shared/Toast';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    updateAlertStatus: vi.fn(),
  },
}));

// Mock framer-motion with dynamic proxy so motion.div, motion.svg, motion.path all render
vi.mock('framer-motion', () => {
  const handler = {
    get: (target, prop) => {
      return ({ children, ...props }) => React.createElement(prop, props, children);
    },
  };
  return {
    motion: new Proxy({}, handler),
    AnimatePresence: ({ children }) => <>{children}</>,
  };
});

const renderWithToast = (ui) => render(<ToastProvider>{ui}</ToastProvider>);

describe('AlertCenterView Component', () => {
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

    // Get all select dropdowns (search, status, grade, risk)
    const selects = screen.getAllByRole('combobox');
    const statusSelect = selects[0]; // first select is status
    fireEvent.change(statusSelect, { target: { value: 'NEW' } });

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

  it('updates alert status from modal select dropdown', async () => {
    api.updateAlertStatus.mockResolvedValue({ status: 'success' });
    const onStatusUpdated = vi.fn();

    renderWithToast(
      <AlertCenterView
        alerts={mockAlerts}
        selectedAlert={mockAlerts[0]}
        onStatusUpdated={onStatusUpdated}
      />
    );

    // Find the triage status select in the modal
    const triageSelect = screen.getByDisplayValue('NEW');
    fireEvent.change(triageSelect, { target: { value: 'INVESTIGATING' } });

    await waitFor(() => {
      expect(api.updateAlertStatus).toHaveBeenCalledWith('ALT-101', 'INVESTIGATING');
      expect(onStatusUpdated).toHaveBeenCalledWith('ALT-101', 'INVESTIGATING');
    });
  });

  it('triggers onLaunchTrace when Trace button in modal is clicked', () => {
    const onLaunchTrace = vi.fn();
    renderWithToast(
      <AlertCenterView
        alerts={mockAlerts}
        selectedAlert={mockAlerts[0]}
        onLaunchTrace={onLaunchTrace}
      />
    );

    const traceBtn = screen.getByRole('button', { name: /Trace Taint Flows/i });
    fireEvent.click(traceBtn);

    expect(onLaunchTrace).toHaveBeenCalledWith('ENT-ALPHA');
  });

  it('triggers onLaunchInvestigate when Case Dossier button is clicked', () => {
    const onLaunchInvestigate = vi.fn();
    renderWithToast(
      <AlertCenterView
        alerts={mockAlerts}
        selectedAlert={mockAlerts[0]}
        onLaunchInvestigate={onLaunchInvestigate}
      />
    );

    const caseBtn = screen.getByRole('button', { name: /Build Case Dossier/i });
    fireEvent.click(caseBtn);

    expect(onLaunchInvestigate).toHaveBeenCalledWith('ENT-ALPHA');
  });
});
