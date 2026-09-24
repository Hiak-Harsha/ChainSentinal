import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CommandPalette from '../components/shell/CommandPalette';

vi.mock('../../api', () => ({
  api: {
    getEntities: vi.fn(() => Promise.resolve([
      { entity_id: 'ENT_REMOTE_01', entity_type: 'EXCHANGE', member_count: 50 },
    ])),
  },
}));

describe('CommandPalette Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <CommandPalette
        isOpen={false}
        onClose={vi.fn()}
        onSelect={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders input, recent entities, alerts, and cases when isOpen is true', () => {
    const alerts = [
      { alert_id: 'ALT_001', entity_id: 'ENT_TARGET_1', typology: 'Peel Chain Dispersion', risk_score: 0.9 },
    ];
    const recentEntities = [
      { entity_id: 'ENT_RECENT_01', entity_type: 'MIXER' },
    ];
    const cases = [
      { case_id: 'CASE_001', title: 'Silk Road Seizure' },
    ];

    render(
      <CommandPalette
        isOpen={true}
        onClose={vi.fn()}
        onSelect={vi.fn()}
        alerts={alerts}
        recentEntities={recentEntities}
        cases={cases}
      />
    );

    expect(screen.getByPlaceholderText(/Type to search entities/i)).toBeInTheDocument();
    expect(screen.getByText('ENT_RECENT_01')).toBeInTheDocument();
    expect(screen.getByText(/Peel Chain Dispersion/i)).toBeInTheDocument();
    expect(screen.getByText('Silk Road Seizure')).toBeInTheDocument();
  });

  it('selects an entity on click', () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();
    const recentEntities = [
      { entity_id: 'ENT_ALPHA', entity_type: 'MIXER' },
      { entity_id: 'ENT_BETA', entity_type: 'EXCHANGE' },
    ];

    render(
      <CommandPalette
        isOpen={true}
        onClose={onClose}
        onSelect={onSelect}
        recentEntities={recentEntities}
      />
    );

    fireEvent.click(screen.getByText('ENT_BETA'));

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
      mode: 'network',
      selection: expect.objectContaining({ id: 'ENT_BETA' }),
    }));
    expect(onClose).toHaveBeenCalled();
  });

  it('closes on Escape key press', () => {
    const onClose = vi.fn();
    render(
      <CommandPalette
        isOpen={true}
        onClose={onClose}
        onSelect={vi.fn()}
      />
    );

    const input = screen.getByPlaceholderText(/Type to search entities/i);
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(onClose).toHaveBeenCalled();
  });
});
