import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CasesView from '../components/CasesView';
import { ToastProvider } from '../components/shared/Toast';

vi.mock('../api', () => ({
  api: {
    getCases: vi.fn(() => Promise.resolve([
      {
        case_id: 'CASE-2026-001',
        target_id: 'ENT_DARK_MARKET',
        title: 'Darknet Market Liquidation',
        status: 'OPEN',
        entities: ['ENT_DARK_MARKET', 'ENT_HOP_1'],
        timeline: [{ event_type: 'SEALED', timestamp: 1700000000 }],
      },
      {
        case_id: 'CASE-2026-002',
        target_id: 'ENT_RANSOM_HUB',
        title: 'Ransomware Extortion Chain',
        status: 'SEALED',
        entities: ['ENT_RANSOM_HUB'],
        timeline: [],
      },
    ])),
    investigate: vi.fn((params) => Promise.resolve({
      case_id: 'CASE-2026-NEW',
      target_id: params.target,
      title: `Forensic Dossier ${params.target}`,
      status: 'OPEN',
    })),
    exportCaseHtml: vi.fn(() => Promise.resolve()),
    exportCaseCsv: vi.fn(() => Promise.resolve()),
  },
}));

const renderWithToast = (ui) => render(<ToastProvider>{ui}</ToastProvider>);

describe('CasesView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders case dossier list and header controls', async () => {
    renderWithToast(<CasesView />);

    expect(await screen.findByText('CASE-2026-001')).toBeInTheDocument();
    expect(screen.getByText('Darknet Market Liquidation')).toBeInTheDocument();
    expect(screen.getByText('CASE-2026-002')).toBeInTheDocument();
    expect(screen.getByText('Ransomware Extortion Chain')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Entity ID \/ Address/i)).toBeInTheDocument();
  });

  it('filters cases live using the search input', async () => {
    renderWithToast(<CasesView />);

    expect(await screen.findByText('CASE-2026-001')).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/Search case dossiers/i);
    fireEvent.change(searchInput, { target: { value: 'Ransomware' } });

    expect(screen.queryByText('CASE-2026-001')).not.toBeInTheDocument();
    expect(screen.getByText('CASE-2026-002')).toBeInTheDocument();
  });

  it('calls onSelectCase when Inspect button or row is clicked', async () => {
    const onSelectCase = vi.fn();
    renderWithToast(<CasesView onSelectCase={onSelectCase} />);

    expect(await screen.findByText('CASE-2026-001')).toBeInTheDocument();

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    expect(onSelectCase).toHaveBeenCalledWith(expect.objectContaining({ case_id: 'CASE-2026-001' }));
  });

  it('calls api.exportCaseHtml when Export Dossier button is clicked', async () => {
    const { api } = await import('../api');
    renderWithToast(<CasesView />);

    expect(await screen.findByText('CASE-2026-001')).toBeInTheDocument();

    const exportDossierBtns = screen.getAllByRole('button', { name: /Export Dossier/i });
    fireEvent.click(exportDossierBtns[0]);

    expect(api.exportCaseHtml).toHaveBeenCalledWith('CASE-2026-001');
  });

  it('calls api.exportCaseCsv when Export Hops CSV button is clicked', async () => {
    const { api } = await import('../api');
    renderWithToast(<CasesView />);

    expect(await screen.findByText('CASE-2026-001')).toBeInTheDocument();

    const exportCsvBtns = screen.getAllByRole('button', { name: /Export Hops CSV/i });
    fireEvent.click(exportCsvBtns[0]);

    expect(api.exportCaseCsv).toHaveBeenCalledWith('CASE-2026-001');
  });
});
