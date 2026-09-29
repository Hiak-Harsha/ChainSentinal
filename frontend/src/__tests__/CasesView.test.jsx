import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CasesView from '../components/CasesView';
import { ToastProvider } from '../components/shared/Toast';

vi.mock('../api', () => ({
  api: {
    getCases: vi.fn(() =>
      Promise.resolve([
        {
          case_id: 'CASE-2026-001',
          target_id: 'ENT_DARK_MARKET',
          title: 'Darknet Market Liquidation',
          status: 'OPEN',
          entities: ['ENT_DARK_MARKET', 'ENT_HOP_1'],
          timeline: [
            {
              event_id: 'evt_01',
              event_type: 'SEALED',
              timestamp: 1700000000,
              details: { note: 'Case opened and flagged' },
            },
          ],
        },
        {
          case_id: 'CASE-2026-002',
          target_id: 'ENT_RANSOM_HUB',
          title: 'Ransomware Extortion Chain',
          status: 'SEALED',
          entities: ['ENT_RANSOM_HUB'],
          timeline: [],
        },
      ])
    ),
    getCaseTimeline: vi.fn((caseId) =>
      Promise.resolve([
        {
          event_id: 'evt_01',
          case_id: caseId,
          event_type: 'SEALED',
          timestamp: 1700000000,
          details: { note: 'Initial dossier compiled' },
        },
      ])
    ),
    addCaseTimelineEvent: vi.fn((caseId, payload) =>
      Promise.resolve({
        event_id: 'evt_99',
        status: 'recorded',
      })
    ),
    investigate: vi.fn((params) =>
      Promise.resolve({
        case_id: 'CASE-2026-NEW',
        target_id: params.target,
        title: `Forensic Dossier ${params.target}`,
        status: 'OPEN',
        entities: [params.target],
        timeline: [],
      })
    ),
    exportCaseHtml: vi.fn(() => Promise.resolve()),
    exportCaseCsv: vi.fn(() => Promise.resolve()),
  },
  API_BASE: 'http://localhost:8000/api',
}));

const renderWithToast = (ui) => render(<ToastProvider>{ui}</ToastProvider>);

describe('CasesView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders case dossier list and header controls', async () => {
    renderWithToast(<CasesView />);

    await waitFor(() => {
      expect(screen.getAllByText('CASE-2026-001').length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText('Darknet Market Liquidation').length).toBeGreaterThan(0);
    expect(screen.getByText('CASE-2026-002')).toBeInTheDocument();
    expect(screen.getByText('Ransomware Extortion Chain')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Entity ID \/ Address/i)).toBeInTheDocument();
  });

  it('filters cases live using the search input', async () => {
    renderWithToast(<CasesView />);

    await waitFor(() => {
      expect(screen.getAllByText('CASE-2026-001').length).toBeGreaterThan(0);
    });

    const searchInput = screen.getByPlaceholderText(/Search case dossiers/i);
    fireEvent.change(searchInput, { target: { value: 'Ransomware' } });

    // In directory table, CASE-2026-001 row should be filtered out
    expect(screen.queryByRole('row', { name: /Darknet/i })).not.toBeInTheDocument();
    expect(screen.getByRole('row', { name: /Ransomware/i })).toBeInTheDocument();
  });

  it('calls onSelectCase when Inspect button or row is clicked', async () => {
    const onSelectCase = vi.fn();
    renderWithToast(<CasesView onSelectCase={onSelectCase} />);

    await waitFor(() => {
      expect(screen.getAllByText('CASE-2026-001').length).toBeGreaterThan(0);
    });

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    expect(onSelectCase).toHaveBeenCalledWith(
      expect.objectContaining({ case_id: 'CASE-2026-001' })
    );
  });

  it('calls api.exportCaseHtml when Export Dossier button is clicked', async () => {
    const { api } = await import('../api');
    renderWithToast(<CasesView />);

    await waitFor(() => {
      expect(screen.getAllByText('CASE-2026-001').length).toBeGreaterThan(0);
    });

    const exportDossierBtns = screen.getAllByRole('button', {
      name: /Export Dossier|Export HTML Dossier/i,
    });
    fireEvent.click(exportDossierBtns[0]);

    expect(api.exportCaseHtml).toHaveBeenCalledWith('CASE-2026-001');
  });

  it('calls api.exportCaseCsv when Export Hops CSV button is clicked', async () => {
    const { api } = await import('../api');
    renderWithToast(<CasesView />);

    await waitFor(() => {
      expect(screen.getAllByText('CASE-2026-001').length).toBeGreaterThan(0);
    });

    const exportCsvBtns = screen.getAllByRole('button', {
      name: /Export Hops CSV/i,
    });
    fireEvent.click(exportCsvBtns[0]);

    expect(api.exportCaseCsv).toHaveBeenCalledWith('CASE-2026-001');
  });

  it('allows recording an audit timeline event into the dossier', async () => {
    const { api } = await import('../api');
    renderWithToast(<CasesView />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Add evidentiary finding/i)).toBeInTheDocument();
    });

    const noteInput = screen.getByPlaceholderText(/Add evidentiary finding/i);
    fireEvent.change(noteInput, {
      target: { value: 'Subpoena delivered to clearinghouse' },
    });

    const submitBtn = screen.getByRole('button', { name: /Record/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.addCaseTimelineEvent).toHaveBeenCalledWith(
        'CASE-2026-001',
        expect.objectContaining({
          target_id: 'ENT_DARK_MARKET',
          details: expect.objectContaining({
            note: 'Subpoena delivered to clearinghouse',
          }),
        })
      );
    });
  });
});
