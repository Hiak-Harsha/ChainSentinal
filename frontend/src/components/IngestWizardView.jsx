import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UploadCloud,
  FileCheck2,
  RefreshCw,
  ShieldCheck,
  CheckCircle2,
  Database,
  FileCode,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Sliders,
  Check,
  Eye,
  FileSpreadsheet,
  Layers,
} from 'lucide-react';
import { api } from '../api';
import {
  PageHeader,
  PageToolbar,
  SectionCard,
  MetricCard,
  DataTable,
  StatusBadge,
  EmptyState,
  LoadingState,
  useToast,
} from './shared';
import { PipelineFlowDiagram } from './visuals/PipelineFlowDiagram';

export default function IngestWizardView() {
  const [wizardStep, setWizardStep] = useState(1); // 1: Select/Inspect, 2: Schema Mapping, 3: Ingest Progress, 4: QC & Quarantine
  const [jobs, setJobs] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedQC, setSelectedQC] = useState(null);
  const [quarantineRecords, setQuarantineRecords] = useState([]);
  const [loadingQuarantine, setLoadingQuarantine] = useState(false);

  // Upload & Schema Inspection State
  const [uploadFile, setUploadFile] = useState(null);
  const [detectingSchema, setDetectingSchema] = useState(false);
  const [schemaResult, setSchemaResult] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [activeJobId, setActiveJobId] = useState(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobStage, setJobStage] = useState('Idle');

  // Quarantine Reason Filter
  const [quarantineReasonFilter, setQuarantineReasonFilter] = useState('ALL');

  const toast = useToast();
  const fileInputRef = useRef(null);
  const pollIntervalRef = useRef(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [jData, pData] = await Promise.all([
        api.getIngestJobs().catch(() => []),
        api.getIngestProfiles().catch(() => []),
      ]);
      setJobs(jData || []);
      setProfiles(pData || []);
      if (jData && jData.length > 0 && !selectedJob) {
        setSelectedJob(jData[0]);
      }
    } catch (err) {
      console.error('Failed to load ingest data:', err);
      toast?.showToast('Failed to load ingestion history', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Fetch QC and Quarantine when selectedJob changes
  useEffect(() => {
    if (!selectedJob?.job_id) {
      setSelectedQC(null);
      return;
    }
    api.getIngestQC(selectedJob.job_id)
      .then(setSelectedQC)
      .catch(() => setSelectedQC(null));

    loadQuarantine();
  }, [selectedJob?.job_id]);

  const loadQuarantine = async (reason = quarantineReasonFilter) => {
    setLoadingQuarantine(true);
    try {
      const params = { limit: 50 };
      if (reason !== 'ALL') params.reason_code = reason;
      const records = await api.getQuarantine(params);
      setQuarantineRecords(records || []);
    } catch (err) {
      setQuarantineRecords([]);
    } finally {
      setLoadingQuarantine(false);
    }
  };

  // Step 1 -> 2: Select file and auto-detect schema
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadFile(file);
    setDetectingSchema(true);
    toast?.showToast(`Inspecting schema for ${file.name}…`, 'info');

    try {
      const result = await api.detectSchema(file);
      setSchemaResult(result);
      setWizardStep(2);
      toast?.showToast(`Schema detected with ${(result.confidence * 100).toFixed(0)}% confidence`, 'success');
    } catch (err) {
      toast?.showToast(`Schema detection error: ${err.message}`, 'error');
      // Still allow proceeding to upload directly if detection fails
      setWizardStep(2);
    } finally {
      setDetectingSchema(false);
    }
  };

  // Quick smoke test dataset loader
  const handleLoadSmokeSample = async () => {
    setDetectingSchema(true);
    toast?.showToast('Loading smoke test fixture…', 'info');
    try {
      const result = await api.detectSchema('chainsentinel_smoke_observations.csv');
      setSchemaResult(result);
      setWizardStep(2);
      toast?.showToast('Smoke test schema verified', 'success');
    } catch (err) {
      toast?.showToast(`Sample schema inspection failed: ${err.message}`, 'error');
    } finally {
      setDetectingSchema(false);
    }
  };

  // Step 2 -> 3: Confirm and execute ingestion
  const handleConfirmIngest = async () => {
    if (!uploadFile) {
      // If using smoke sample without uploadFile, trigger demo upload
      toast?.showToast('Please select a file to ingest', 'warning');
      return;
    }

    setUploading(true);
    setWizardStep(3);
    setJobProgress(0.1);
    setJobStage('Uploading dataset…');

    try {
      const startRes = await api.uploadIngest(uploadFile);
      const jobId = startRes.job_id;
      setActiveJobId(jobId);
      setJobProgress(0.35);
      setJobStage('Parsing and validating records…');

      // Poll job status until complete
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(async () => {
        try {
          const job = await api.getIngestJob(jobId);
          if (job) {
            if (job.status === 'completed') {
              clearInterval(pollIntervalRef.current);
              setJobProgress(1.0);
              setJobStage('Complete');
              setUploading(false);
              toast?.showToast(`Ingestion completed: ${job.valid_rows} valid records`, 'success');
              await loadData();
              setSelectedJob(job);
              setWizardStep(4);
            } else if (job.status === 'failed') {
              clearInterval(pollIntervalRef.current);
              setUploading(false);
              toast?.showToast('Ingestion pipeline failed', 'error');
            } else {
              setJobProgress((prev) => Math.min(0.9, prev + 0.15));
            }
          }
        } catch (e) {
          // ignore transient poll error
        }
      }, 800);
    } catch (err) {
      setUploading(false);
      toast?.showToast(`Upload failed: ${err.message}`, 'error');
      setWizardStep(2);
    }
  };

  const getQcBadge = (rate) => {
    if (rate >= 0.95) return <StatusBadge status="PASS" />;
    if (rate >= 0.80) return <StatusBadge status="WARNING" />;
    return <StatusBadge status="FAILED" />;
  };

  return (
    <div style={{ position: 'relative', width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header Bar */}
      <PageHeader
        icon={UploadCloud}
        iconColor="var(--btc-orange)"
        title="Forensic Data Ingestion &amp; Schema Mapping Wizard"
        subtitle="Streaming parser (CSV/JSON/XML), 7-category quarantine validator, and Data-Quality telemetry auditing."
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input
              type="file"
              ref={fileInputRef}
              accept=".csv,.json,.xml"
              hidden
              onChange={handleFileSelect}
            />
            <button
              className="btn btn-secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={detectingSchema || uploading}
            >
              <UploadCloud size={14} />
              {uploadFile ? uploadFile.name : 'Select Dataset (CSV/JSON/XML)'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleLoadSmokeSample}
              disabled={detectingSchema || uploading}
              title="Inspect registered smoke observations fixture"
            >
              <FileSpreadsheet size={14} />
              Load Smoke Sample
            </button>
            <button className="btn btn-secondary" onClick={loadData} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        }
      />

      {/* 4-Stage Ingestion Pipeline Flow Diagram */}
      <PipelineFlowDiagram currentStep={wizardStep} fileCount={jobs.length} />

      {/* Wizard Step 2: Schema Mapping Review (When file is chosen) */}
      {wizardStep === 2 && schemaResult && (
        <SectionCard
          icon={Sliders}
          iconColor="var(--color-primary)"
          title={`Schema Mapping Review: ${schemaResult.file_name || uploadFile?.name || 'Dataset'}`}
          subtitle={`Auto-detected with ${(schemaResult.confidence * 100).toFixed(0)}% confidence across ${schemaResult.headers?.length ?? '—'} fields`}
          actions={
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setWizardStep(1)}>
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleConfirmIngest}
                disabled={uploading}
              >
                <Check size={14} /> Confirm &amp; Execute Ingestion
              </button>
            </div>
          }
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <div className="inspector-section-title">Detected Field Mappings</div>
              <div style={{ maxHeight: '240px', overflowY: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
                <table style={{ width: '100%', fontSize: '0.78rem', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border-subtle)' }}>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: 'var(--text-dim)' }}>Source Header</th>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'left', color: 'var(--text-dim)' }}>Canonical Target</th>
                      <th style={{ padding: '0.4rem 0.6rem', textAlign: 'right', color: 'var(--text-dim)' }}>Match Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(schemaResult.mapping_details || []).map((m, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}>
                        <td className="mono" style={{ padding: '0.4rem 0.6rem', color: 'var(--text-main)' }}>{m.source_column}</td>
                        <td className="mono font-semibold" style={{ padding: '0.4rem 0.6rem', color: 'var(--color-primary)' }}>&rarr; {m.target_canonical}</td>
                        <td style={{ padding: '0.4rem 0.6rem', textAlign: 'right' }}>
                          <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>{m.match_type}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div>
              <div className="inspector-section-title">Sample Ingest Preview (First 5 Rows)</div>
              <div style={{ maxHeight: '240px', overflowX: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '0.5rem', background: 'rgba(0, 0, 0, 0.2)' }}>
                <pre style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: 0 }}>
                  {JSON.stringify(schemaResult.sample_rows || schemaResult.preview_rows || [], null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      {/* Wizard Step 3: Ingestion In-Progress State */}
      {wizardStep === 3 && (
        <SectionCard
          icon={UploadCloud}
          iconColor="var(--btc-orange)"
          title="Executing Forensic Data Ingestion"
          subtitle={`Streaming transactions, calculating cryptographic checksums, and filtering quarantine violations.`}
        >
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2rem 1rem' }}>
            <div
              style={{
                width: '100%',
                maxWidth: '480px',
                height: '8px',
                background: 'rgba(255, 255, 255, 0.06)',
                borderRadius: '4px',
                overflow: 'hidden',
                marginBottom: '1rem',
              }}
            >
              <div
                style={{
                  width: `${jobProgress * 100}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, var(--btc-orange), var(--emerald))',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-emphasis)', marginBottom: '0.25rem' }}>
              {jobStage}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Job ID: <span className="mono">{activeJobId || 'Initializing…'}</span> &bull; {(jobProgress * 100).toFixed(0)}% Complete
            </div>
          </div>
        </SectionCard>
      )}

      {/* Main Grid: Left = Ingest Jobs Ledger; Right = Real QC Report & Quarantine Inspector */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1.25rem' }}>
        {/* Left: Ingest Jobs History */}
        <SectionCard
          icon={FileCheck2}
          iconColor="var(--emerald)"
          title={`Ingestion Jobs History (${jobs.length})`}
          subtitle="Select a job run to inspect its authentic forensic Data-Quality report"
        >
          {jobs.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '420px', overflowY: 'auto' }}>
              {jobs.map((job) => {
                const isSelected = selectedJob?.job_id === job.job_id;
                return (
                  <div
                    key={job.job_id}
                    onClick={() => {
                      setSelectedJob(job);
                      setWizardStep(4);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.7rem 0.85rem',
                      background: isSelected ? 'rgba(247, 147, 26, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                      border: `1px solid ${isSelected ? 'var(--color-primary)' : 'var(--border-subtle)'}`,
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="mono font-semibold" style={{ color: isSelected ? 'var(--color-primary)' : 'var(--text-main)', fontSize: '0.82rem' }}>
                          {job.job_id}
                        </span>
                        <span className="badge badge-emerald mono" style={{ fontSize: '0.65rem' }}>
                          {job.format || 'CSV'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                        Processed: <strong className="mono">{job.total_rows?.toLocaleString() ?? 0}</strong> &bull; Valid: <strong className="text-emerald mono">{job.valid_rows?.toLocaleString() ?? 0}</strong> &bull; Quarantined: <strong className="text-crimson mono">{job.quarantined_rows?.toLocaleString() ?? 0}</strong>
                      </div>
                    </div>
                    <StatusBadge status={job.status || 'COMPLETED'} size="sm" />
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={UploadCloud}
              title="No Ingestion Runs Recorded"
              description="Upload a dataset or load the smoke sample to initiate data processing."
            />
          )}
        </SectionCard>

        {/* Right: Authentic QC Telemetry Report */}
        <SectionCard
          icon={ShieldCheck}
          iconColor="var(--emerald)"
          title="Forensic Data-Quality &amp; Quarantine Audit"
          subtitle={selectedJob ? `Verified telemetry from job ${selectedJob.job_id}` : 'Select an ingestion job to inspect QC report'}
          actions={
            selectedQC?.valid_rate !== undefined && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Completeness:</span>
                <span className="mono font-bold" style={{ color: 'var(--emerald)' }}>
                  {(selectedQC.valid_rate * 100).toFixed(1)}%
                </span>
                {getQcBadge(selectedQC.valid_rate)}
              </div>
            )
          }
        >
          {selectedQC ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="quality-metric-grid">
                {[
                  ['Rows Processed', selectedQC.total_rows_processed],
                  ['Valid Records', selectedQC.valid_rows],
                  ['Quarantined Records', selectedQC.quarantined_rows],
                  ['Duplicate Rows', selectedQC.duplicate_rows],
                  ['Unique Transactions', selectedQC.unique_transactions],
                  ['Unique Addresses', selectedQC.unique_addresses],
                  ['Unique IPs', selectedQC.unique_ips],
                  ['Throughput', selectedQC.throughput_rows_per_sec !== undefined ? `${selectedQC.throughput_rows_per_sec}/s` : '—'],
                ].map(([label, value]) => (
                  <div className="quality-metric" key={label}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>{label}</span>
                    <strong className="mono" style={{ color: 'var(--text-emphasis)', fontSize: '0.85rem' }}>
                      {typeof value === 'number' ? value.toLocaleString() : value}
                    </strong>
                  </div>
                ))}
              </div>

              {/* Quarantine Breakdown by Rule */}
              {selectedQC.error_breakdown && Object.keys(selectedQC.error_breakdown).length > 0 && (
                <div>
                  <div className="inspector-section-title">Quarantine Violations by Code</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {Object.entries(selectedQC.error_breakdown).map(([reason, count]) => (
                      <div
                        key={reason}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '0.4rem 0.65rem',
                          background: 'rgba(244, 63, 94, 0.06)',
                          border: '1px solid rgba(244, 63, 94, 0.2)',
                          borderRadius: 'var(--radius-xs)',
                          fontSize: '0.78rem',
                        }}
                      >
                        <span className="mono" style={{ color: 'var(--crimson)' }}>{reason}</span>
                        <strong className="mono" style={{ color: 'var(--text-emphasis)' }}>{count} records</strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              icon={ShieldAlert}
              title="QC Report Pending"
              description="Select an ingestion job from the left ledger to review its verified quality telemetry."
            />
          )}
        </SectionCard>
      </div>

      {/* Quarantine Table Inspector */}
      <SectionCard
        icon={ShieldAlert}
        iconColor="var(--crimson)"
        title={`Quarantine Registry Inspector (${quarantineRecords.length} records)`}
        subtitle="Individual records quarantined by the validator with exact failure reasons and payload"
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <select
              className="select"
              value={quarantineReasonFilter}
              onChange={(e) => {
                setQuarantineReasonFilter(e.target.value);
                loadQuarantine(e.target.value);
              }}
              style={{ fontSize: '0.75rem', height: '28px', padding: '0 0.5rem' }}
            >
              <option value="ALL">All Violation Codes</option>
              <option value="INVALID_TXID">INVALID_TXID</option>
              <option value="AMOUNT_MISMATCH">AMOUNT_MISMATCH</option>
              <option value="TIMESTAMP_ANOMALY">TIMESTAMP_ANOMALY</option>
              <option value="DUPLICATE_ROW">DUPLICATE_ROW</option>
              <option value="PARSER_ERROR">PARSER_ERROR</option>
            </select>
            <button className="btn btn-secondary btn-sm" onClick={() => loadQuarantine(quarantineReasonFilter)}>
              <RefreshCw size={12} className={loadingQuarantine ? 'animate-spin' : ''} />
            </button>
          </div>
        }
      >
        <DataTable
          columns={[
            {
              header: 'Observation ID',
              key: 'obs_id',
              render: (val) => <span className="mono font-semibold">{val?.slice(0, 16)}…</span>,
            },
            {
              header: 'Violation Code',
              key: 'reason_code',
              render: (val, row) => (
                <span className="badge badge-crimson mono" style={{ fontSize: '0.7rem' }}>
                  {val || row.quarantine_reason || 'VIOLATION'}
                </span>
              ),
            },
            {
              header: 'Error Details',
              key: 'error_details',
              render: (val) => (
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  {val || 'Failed validation schema'}
                </span>
              ),
            },
            {
              header: 'Ingested At',
              key: 'ingested_at',
              render: (val) => (
                <span className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                  {val ? new Date(val * 1000).toLocaleTimeString() : '—'}
                </span>
              ),
            },
            {
              header: 'Raw Payload',
              key: 'raw_data',
              render: (val) => (
                <span
                  className="mono text-muted"
                  style={{
                    fontSize: '0.68rem',
                    maxWidth: '220px',
                    display: 'inline-block',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={typeof val === 'string' ? val : JSON.stringify(val)}
                >
                  {typeof val === 'string' ? val : JSON.stringify(val)}
                </span>
              ),
            },
          ]}
          data={quarantineRecords}
          loading={loadingQuarantine}
          emptyTitle="Quarantine Registry Clear"
          emptyDescription="Zero invalid records found matching the active quarantine reason filter."
          pageSize={10}
        />
      </SectionCard>
    </div>
  );
}
