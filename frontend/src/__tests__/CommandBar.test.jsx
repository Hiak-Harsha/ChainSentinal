import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CommandBar from '../components/shell/CommandBar';

vi.mock('../components/charts/AlertSparkline', () => ({
  default: () => <div data-testid="alert-sparkline" />,
}));

describe('CommandBar Component', () => {
  it('renders branding, search bar, mode buttons and status pill', () => {
    render(
      <CommandBar
        mode="overview"
        setMode={vi.fn()}
        searchQuery=""
        onSearchChange={vi.fn()}
        entityCount={1420}
        alertCount={12}
        health={{ status: 'ok' }}
      />
    );

    expect(screen.getByText('ChainSentinel')).toBeInTheDocument();
    expect(screen.getByText('LIVE')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Network')).toBeInTheDocument();
    expect(screen.getByText('Alerts')).toBeInTheDocument();
  });

  it('switches modes when mode button is clicked', () => {
    const setMode = vi.fn();
    render(
      <CommandBar
        mode="overview"
        setMode={setMode}
        searchQuery=""
        onSearchChange={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Network/i }));
    expect(setMode).toHaveBeenCalledWith('network');

    fireEvent.click(screen.getByRole('button', { name: /Alerts/i }));
    expect(setMode).toHaveBeenCalledWith('alerts');
  });

  it('calls onSearchChange when input value changes', () => {
    const onSearchChange = vi.fn();
    render(
      <CommandBar
        mode="overview"
        setMode={vi.fn()}
        searchQuery=""
        onSearchChange={onSearchChange}
      />
    );

    const input = screen.getByPlaceholderText(/Search entities, alerts, addresses/i);
    fireEvent.change(input, { target: { value: 'bc1qtest' } });
    expect(onSearchChange).toHaveBeenCalledWith('bc1qtest');
  });

  it('triggers onOpenPalette and onOpenShortcuts when respective triggers are clicked', () => {
    const onOpenPalette = vi.fn();
    const onOpenShortcuts = vi.fn();
    const onAlertBellClick = vi.fn();

    render(
      <CommandBar
        mode="overview"
        setMode={vi.fn()}
        searchQuery=""
        onSearchChange={vi.fn()}
        onOpenPalette={onOpenPalette}
        onOpenShortcuts={onOpenShortcuts}
        onAlertBellClick={onAlertBellClick}
      />
    );

    // Click ⌘K kbd
    fireEvent.click(screen.getByText('⌘K'));
    expect(onOpenPalette).toHaveBeenCalled();

    // Click ? shortcuts button
    fireEvent.click(screen.getByTitle(/Keyboard Shortcuts/i));
    expect(onOpenShortcuts).toHaveBeenCalled();

    // Click alert bell
    fireEvent.click(screen.getByTitle(/Open Alert Center/i));
    expect(onAlertBellClick).toHaveBeenCalled();
  });
});
