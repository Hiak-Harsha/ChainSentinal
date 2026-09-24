import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ContextRail from '../components/shell/ContextRail';

describe('ContextRail Component', () => {
  it('renders empty recent entities state when list is empty', () => {
    render(<ContextRail recentEntities={[]} onPivotTo={vi.fn()} />);

    expect(screen.getByText('Recent Entities')).toBeInTheDocument();
    expect(screen.getByText('No recent entities')).toBeInTheDocument();
  });

  it('renders active case and triggers onPivotTo when clicked', () => {
    const onPivotTo = vi.fn();
    const activeCase = {
      case_id: 'CASE_ALPHA_001',
      title: 'Darknet Vendor SilkRoute',
      entity_count: 5,
    };

    render(
      <ContextRail
        activeCase={activeCase}
        recentEntities={[]}
        onPivotTo={onPivotTo}
      />
    );

    expect(screen.getByText('Darknet Vendor SilkRoute')).toBeInTheDocument();
    expect(screen.getByText(/5 entities tracked/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Darknet Vendor SilkRoute'));
    expect(onPivotTo).toHaveBeenCalledWith({
      mode: 'network',
      selection: { type: 'case', id: 'CASE_ALPHA_001' },
    });
  });

  it('renders recent entities and triggers onPivotTo with entity details on click', () => {
    const onPivotTo = vi.fn();
    const recentEntities = [
      { entity_id: 'ENT_EXCHANGE_1', entity_type: 'EXCHANGE' },
      { entity_id: 'ENT_MIXER_2', entity_type: 'MIXER' },
    ];

    render(
      <ContextRail
        recentEntities={recentEntities}
        onPivotTo={onPivotTo}
      />
    );

    // Each entity is truncated in the UI
    const entityItems = screen.getAllByText(/ENT_/i);
    expect(entityItems.length).toBeGreaterThanOrEqual(2);

    fireEvent.click(entityItems[0]);
    expect(onPivotTo).toHaveBeenCalledWith({
      mode: 'network',
      selection: { type: 'entity', id: 'ENT_EXCHANGE_1' },
    });
  });
});
