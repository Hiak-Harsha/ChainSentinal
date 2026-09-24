import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import InspectorPanel from '../components/shell/InspectorPanel';
import { ToastProvider } from '../components/shared/Toast';

vi.mock('../components/shared/RiskGauge', () => ({
  default: ({ score }) => <div data-testid="risk-gauge">Risk: {score}</div>,
}));

vi.mock('../components/process/ShapWaterfall', () => ({
  default: () => <div data-testid="shap-waterfall" />,
}));

const renderWithToast = (ui) => render(<ToastProvider>{ui}</ToastProvider>);

describe('InspectorPanel Component', () => {
  it('renders empty prompt when no selection is active', () => {
    render(<InspectorPanel selection={null} />);

    expect(screen.getByText(/No Selection/i)).toBeInTheDocument();
    expect(screen.getByText(/Click an entity, alert, or trace result to inspect it here/i)).toBeInTheDocument();
  });

  it('renders entity details and fires actions when buttons are clicked', () => {
    const onLaunchTrace = vi.fn();
    const onInvestigate = vi.fn();
    const onClearSelection = vi.fn();

    const entityDetail = {
      entity_id: 'ENT_EXCHANGE_BINANCE_01',
      entity_type: 'EXCHANGE',
      risk_score: 82,
      member_count: 145,
      total_received_sat: 500000000,
      total_sent_sat: 450000000,
    };

    renderWithToast(
      <InspectorPanel
        selection={{ type: 'entity', id: 'ENT_EXCHANGE_BINANCE_01' }}
        entityDetail={entityDetail}
        onLaunchTrace={onLaunchTrace}
        onInvestigate={onInvestigate}
        onClearSelection={onClearSelection}
      />
    );

    expect(screen.getByText('EXCHANGE')).toBeInTheDocument();
    expect(screen.getByTestId('risk-gauge')).toHaveTextContent('82');

    // Click Trace
    const traceBtn = screen.getByRole('button', { name: /Trace/i });
    fireEvent.click(traceBtn);
    expect(onLaunchTrace).toHaveBeenCalledWith('ENT_EXCHANGE_BINANCE_01');

    // Click Investigate
    const invBtn = screen.getByRole('button', { name: /Investigate/i });
    fireEvent.click(invBtn);
    expect(onInvestigate).toHaveBeenCalledWith('ENT_EXCHANGE_BINANCE_01');

    // Click Close
    const closeBtn = screen.getByTitle('Clear selection');
    fireEvent.click(closeBtn);
    expect(onClearSelection).toHaveBeenCalled();
  });

  it('renders alert triage details when an alert selection is provided', () => {
    const onAlertAction = vi.fn();
    const alertDetail = {
      id: 'ALT_9001',
      rule: 'High Velocity Peel Chain',
      status: 'new',
      priority: 4,
      risk_score: 95,
      shap_explanation: [],
    };

    renderWithToast(
      <InspectorPanel
        selection={{ type: 'alert', id: 'ALT_9001' }}
        alertDetail={alertDetail}
        onAlertAction={onAlertAction}
      />
    );

    expect(screen.getByText(/High Velocity Peel Chain/i)).toBeInTheDocument();
    expect(screen.getByTestId('risk-gauge')).toHaveTextContent('95');
  });
});
