import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import IngestWizardView from '../components/IngestWizardView';
import { ToastProvider } from '../components/shared/Toast';

vi.mock('../api', () => ({
  api: {
    getIngestJobs: vi.fn(() =>
      Promise.resolve([
        {
          job_id: 'job_test_01',
          format: 'csv',
          status: 'completed',
          total_rows: 20,
          valid_rows: 18,
          quarantined_rows: 2,
        },
      ])
    ),
    getIngestProfiles: vi.fn(() => Promise.resolve([])),
    getIngestQC: vi.fn(() =>
      Promise.resolve({
        total_rows_processed: 20,
        valid_rows: 18,
        quarantined_rows: 2,
        duplicate_rows: 0,
        unique_transactions: 15,
        unique_addresses: 30,
        unique_ips: 10,
        valid_rate: 0.9,
        throughput_rows_per_sec: 1400,
        error_breakdown: { INVALID_TXID: 2 },
      })
    ),
    getQuarantine: vi.fn(() =>
      Promise.resolve([
        {
          obs_id: 'obs_bad_01',
          reason_code: 'INVALID_TXID',
          error_details: 'Non-hex character in txid',
          raw_data: '{"txid":"invalid_123"}',
          ingested_at: 1704120973,
        },
      ])
    ),
    detectSchema: vi.fn(() =>
      Promise.resolve({
        file_name: 'test.csv',
        confidence: 0.95,
        headers: ['timestamp', 'src_ip', 'txid'],
        mapping_details: [
          { source_column: 'timestamp', target_canonical: 'ts', match_type: 'EXACT' },
        ],
      })
    ),
    uploadIngest: vi.fn(() =>
      Promise.resolve({
        job_id: 'job_upload_02',
        status: 'started',
      })
    ),
    getIngestJob: vi.fn(() =>
      Promise.resolve({
        job_id: 'job_upload_02',
        status: 'completed',
        valid_rows: 18,
        quarantined_rows: 2,
      })
    ),
  },
}));

function renderWithToast(ui) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

describe('IngestWizardView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ingestion wizard header and job history ledger', async () => {
    renderWithToast(<IngestWizardView />);

    expect(screen.getByText(/Forensic Data Ingestion & Schema Mapping Wizard/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText(/job_test_01/i).length).toBeGreaterThan(0);
    });
  });

  it('loads authentic QC telemetry for selected job', async () => {
    renderWithToast(<IngestWizardView />);

    await waitFor(() => {
      expect(screen.getByText(/Rows Processed/i)).toBeInTheDocument();
      expect(screen.getAllByText(/INVALID_TXID/i).length).toBeGreaterThan(0);
    });
  });

  it('renders quarantine registry inspector with quarantined observations', async () => {
    renderWithToast(<IngestWizardView />);

    await waitFor(() => {
      expect(screen.getByText(/Non-hex character in txid/i)).toBeInTheDocument();
    });
  });
});
