import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  PlusCircle,
  FolderOpen,
  Printer,
  FileSpreadsheet,
  Search,
  ShieldCheck,
  Clock,
  Send,
  AlertOctagon,
  Layers,
  ChevronRight,
  ExternalLink,
  Tag,
  CheckCircle2,
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
  ErrorState,
  FilterBar,
  ActionGroup,
  useToast,
  CopyHash,
} from './shared';
import { SealedDossierIcon } from './visuals/icons';

const STATUS_FILTERS = [
  { id: 'ALL', label: 'All Cases' },
  { id: 'OPEN', label: 'Active / Open' },
  { id: 'IN_REVIEW', label: 'In Review' },
  { id: 'SEALED', label: 'Court Sealed' },
  { id: 'RESOLVED', label: 'Resolved' },
];

const EVENT_TYPE_OPTIONS = [
  { value: 'ANALYST_NOTE', label: 'Analyst Note' },
  { value: 'TAINT_CORROBORATION', label: 'Taint Trace Corroboration' },
  { value: 'SUBPOENA_FILED', label: 'Subpoena / LE Notice Filed' },
  { value: 'EXCHANGE_FREEZE', label: 'Exchange Freeze Request' },
  { value: 'OFFCHAIN_INTEL', label: 'Off-Chain OSINT Corroboration' },
];

export default function CasesView({
  prefilledTarget = '',
  onSelectCase,
  selectedCaseId = null,
}) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Currently focused case in main workspace
  const [selectedCase, setSelectedCase] = useState(null);
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  // New investigation launch bar
  const [newTarget, setNewTarget] = useState(prefilledTarget || '');
  const [investigating, setInvestigating] = useState(false);

  // New timeline event form state
  const [newEventText, setNewEventText] = useState('');
  const [newEventType, setNewEventType] = useState('ANALYST_NOTE');
  const [submittingEvent, setSubmittingEvent] = useState(false);

  const toast = useToast();

  const loadCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCases();
      const caseList = data || [];
      setCases(caseList);

      // If selectedCaseId was provided or exists, select it
      if (selectedCaseId) {
        const found = caseList.find(
          (c) => (c.case_data || c).case_id === selectedCaseId
        );
        if (found) {
          handleSelectCase(found.case_data || found);
        }
      } else if (caseList.length > 0 && !selectedCase) {
        handleSelectCase(caseList[0].case_data || caseList[0]);
      }
    } catch (err) {
      console.error('Failed to fetch cases:', err);
      setError(err.message || 'Failed to load case dossiers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleSelectCase = async (cData) => {
    setSelectedCase(cData);
    if (onSelectCase) onSelectCase(cData);

    const cid = cData.case_id;
    if (!cid) return;

    setLoadingTimeline(true);
    try {
      const tl = await api.getCaseTimeline(cid);
      setTimelineEvents(tl || cData.timeline || []);
    } catch (err) {
      // Fallback to inline case timeline if available
      setTimelineEvents(cData.timeline || []);
    } finally {
      setLoadingTimeline(false);
    }
  };

  const handleLaunchInvestigate = async () => {
    if (!newTarget.trim()) return;
    setInvestigating(true);
    toast?.showToast(
      `Compiling forensic dossier for ${newTarget.slice(0, 12)}...`,
      'info'
    );
    try {
      const newCase = await api.investigate({
        target: newTarget.trim(),
        max_hops: 4,
        decay_model: 'proportional',
      });
      await loadCases();
      const unwrapped = newCase.case_data || newCase;
      handleSelectCase(unwrapped);
      toast?.showToast(
        `Investigation dossier ${unwrapped.case_id || ''} sealed and archived`,
        'success'
      );
      setNewTarget('');
    } catch (err) {
      toast?.showToast(`Investigation failed: ${err.message}`, 'error');
    } finally {
      setInvestigating(false);
    }
  };

  const handleAddTimelineEvent = async (e) => {
    e.preventDefault();
    if (!selectedCase?.case_id || !newEventText.trim()) return;
    setSubmittingEvent(true);
    try {
      const cid = selectedCase.case_id;
      const payload = {
        event_type: newEventType,
        target_id: selectedCase.target_id || selectedCase.case_id,
        details: {
          note: newEventText.trim(),
          recorded_by: 'Lead Forensic Examiner',
        },
      };
      await api.addCaseTimelineEvent(cid, payload);

      // Refresh timeline
      const updatedTl = await api.getCaseTimeline(cid).catch(() => null);
      if (updatedTl) {
        setTimelineEvents(updatedTl);
      } else {
        setTimelineEvents((prev) => [
          ...prev,
          {
            event_id: `local_${Date.now()}`,
            case_id: cid,
            event_type: newEventType,
            target_id: payload.target_id,
            timestamp: Date.now() / 1000,
            details: payload.details,
          },
        ]);
      }
      setNewEventText('');
      toast?.showToast('Forensic timeline audit event recorded', 'success');
    } catch (err) {
      toast?.showToast(`Failed to record audit event: ${err.message}`, 'error');
    } finally {
      setSubmittingEvent(false);
    }
  };

  const handleExportHtml = async (e, caseObj) => {
    e?.stopPropagation();
    const cData = caseObj?.case_data || caseObj || selectedCase;
    const cid = cData?.case_id;
    if (!cid) return;
    try {
      toast?.showToast(`Opening HTML forensic dossier for ${cid}...`, 'info');
      await api.exportCaseHtml(cid);
    } catch (err) {
      toast?.showToast(`Export dossier failed: ${err.message}`, 'error');
    }
  };

  const handleExportCsv = async (e, caseObj) => {
    e?.stopPropagation();
    const cData = caseObj?.case_data || caseObj || selectedCase;
    const cid = cData?.case_id;
    if (!cid) return;
    try {
      toast?.showToast(`Exporting hops CSV for ${cid}...`, 'info');
      await api.exportCaseCsv(cid);
      toast?.showToast(`Downloaded ${cid}_hops.csv`, 'success');
    } catch (err) {
      toast?.showToast(`Export hops CSV failed: ${err.message}`, 'error');
    }
  };

  // Filter cases
  const filteredCases = cases.filter((c) => {
    const cData = c.case_data || c;
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      !searchTerm ||
      cData.case_id?.toLowerCase().includes(q) ||
      cData.target_id?.toLowerCase().includes(q) ||
      cData.title?.toLowerCase().includes(q);

    const matchesStatus =
      statusFilter === 'ALL' ||
      (cData.status || 'OPEN').toUpperCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // Directory KPI metrics
  const totalCases = cases.length;
  const activeCases = cases.filter(
    (c) => (c.case_data || c).status === 'OPEN'
  ).length;
  const sealedCases = cases.filter(
    (c) =>
      (c.case_data || c).status === 'SEALED' ||
      (c.case_data || c).status === 'RESOLVED'
  ).length;

  const currentCase = selectedCase?.case_data || selectedCase;

  // Table columns configuration
  const directoryColumns = [
    {
      header: 'Seal',
      id: 'seal',
      width: '55px',
      cell: (row) => {
        const cData = row.case_data || row;
        const isVerified =
          cData.status === 'RESOLVED' || cData.status === 'SEALED';
        return <SealedDossierIcon size={20} verified={isVerified} />;
      },
    },
    {
      header: 'Case ID',
      id: 'case_id',
      sortable: true,
      cell: (row) => {
        const cData = row.case_data || row;
        return (
          <span
            className="mono"
            style={{
              fontWeight: 700,
              fontSize: '0.8rem',
              color: 'var(--text-emphasis)',
            }}
          >
            {cData.case_id}
          </span>
        );
      },
    },
    {
      header: 'Target Entity',
      id: 'target',
      cell: (row) => {
        const cData = row.case_data || row;
        return (
          <CopyHash
            value={cData.target_id}
            label="Target"
            truncateLength={8}
          />
        );
      },
    },
    {
      header: 'Title / Subject',
      id: 'title',
      cell: (row) => {
        const cData = row.case_data || row;
        return (
          <span
            style={{
              fontWeight: 600,
              color: 'var(--text-main)',
              fontSize: '0.82rem',
            }}
          >
            {cData.title || `Forensic Dossier ${cData.case_id}`}
          </span>
        );
      },
    },
    {
      header: 'Entities',
      id: 'entities',
      width: '70px',
      cell: (row) => {
        const cData = row.case_data || row;
        const cnt = cData.entities
          ? cData.entities.length
          : (cData.entity_count ?? 1);
        return (
          <span
            className="mono"
            style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}
          >
            {cnt}
          </span>
        );
      },
    },
    {
      header: 'Events',
      id: 'events',
      width: '70px',
      cell: (row) => {
        const cData = row.case_data || row;
        const cnt = cData.timeline
          ? cData.timeline.length
          : (cData.events_count ?? 0);
        return (
          <span
            className="mono"
            style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}
          >
            {cnt}
          </span>
        );
      },
    },
    {
      header: 'Status',
      id: 'status',
      width: '100px',
      cell: (row) => {
        const cData = row.case_data || row;
        return <StatusBadge status={cData.status || 'OPEN'} size="sm" />;
      },
    },
    {
      header: 'Actions',
      id: 'actions',
      width: '280px',
      cell: (row) => {
        const cData = row.case_data || row;
        return (
          <div
            style={{ display: 'flex', gap: '0.4rem' }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => handleSelectCase(cData)}
            >
              Inspect
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={(e) => handleExportHtml(e, cData)}
              title="Export Forensic Dossier (HTML/Print)"
            >
              <Printer size={12} style={{ marginRight: '0.25rem' }} />
              Export Dossier
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={(e) => handleExportCsv(e, cData)}
              title="Export Hops (CSV)"
            >
              <FileSpreadsheet size={12} style={{ marginRight: '0.25rem' }} />
              Export Hops CSV
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
      }}
    >
      {/* Page Header */}
      <PageHeader
        icon={FileText}
        title="Autonomous Forensic Case Dossiers & Dossier Workspace"
        subtitle="Court-admissible evidentiary case files, deterministic chain of custody, timeline audit trails, and multi-format exports."
        actions={
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              flexWrap: 'wrap',
            }}
          >
            <input
              type="text"
              className="input mono"
              style={{ width: '220px' }}
              placeholder="Entity ID / Address..."
              value={newTarget}
              onChange={(e) => setNewTarget(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleLaunchInvestigate()}
            />
            <button
              className="btn btn-primary"
              onClick={handleLaunchInvestigate}
              disabled={investigating || !newTarget.trim()}
            >
              <PlusCircle size={15} />
              {investigating ? 'Investigating...' : 'Generate Case'}
            </button>
          </div>
        }
      />

      {/* Case Directory KPIs */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
        }}
      >
        <MetricCard
          label="Registered Dossiers"
          value={totalCases}
          icon={FolderOpen}
          accentColor="var(--btc-orange)"
          helper="Total evidentiary case files in repository"
        />
        <MetricCard
          label="Active Investigations"
          value={activeCases}
          icon={Clock}
          accentColor="var(--color-primary)"
          helper="Unresolved cases pending forensic closure"
        />
        <MetricCard
          label="Sealed Court Records"
          value={sealedCases}
          icon={ShieldCheck}
          accentColor="var(--emerald)"
          helper="Digitally sealed court-admissible dossiers"
        />
      </div>

      {/* Case Directory Section Card */}
      <SectionCard
        icon={FolderOpen}
        iconColor="var(--btc-orange)"
        title={`Forensic Case Directory (${filteredCases.length})`}
        subtitle="Chronological register of autonomous and investigator-initiated case files."
        actions={
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              flexWrap: 'wrap',
            }}
          >
            <FilterBar
              filters={STATUS_FILTERS}
              activeFilter={statusFilter}
              onSelect={setStatusFilter}
            />
            <div style={{ position: 'relative', width: '220px' }}>
              <Search
                size={14}
                style={{
                  position: 'absolute',
                  left: '0.65rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-dim)',
                }}
              />
              <input
                type="text"
                className="input"
                style={{
                  width: '100%',
                  paddingLeft: '2rem',
                  fontSize: '0.78rem',
                }}
                placeholder="Search case dossiers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        }
      >
        {loading ? (
          <LoadingState message="Querying case dossiers from database..." />
        ) : error ? (
          <ErrorState
            title="Failed to Load Cases"
            message={error}
            onRetry={loadCases}
          />
        ) : (
          <DataTable
            columns={directoryColumns}
            data={filteredCases}
            keyExtractor={(row) => (row.case_data || row).case_id}
            onRowClick={(row) => handleSelectCase(row.case_data || row)}
            selectedRowKey={currentCase?.case_id}
            emptyMessage="No case dossiers found matching filters. Enter an entity above to generate an investigation."
            pageSize={10}
          />
        )}
      </SectionCard>

      {/* Selected Case Workspace (Occupies primary workspace naturally, not a popup) */}
      {currentCase && (
        <SectionCard
          icon={FileText}
          iconColor="var(--color-primary)"
          title={`Forensic Dossier Workspace: ${currentCase.case_id}`}
          subtitle={`Target: ${currentCase.target_id || 'N/A'} — Created ${currentCase.created_at ? new Date(currentCase.created_at * 1000).toLocaleString() : 'Recently'}`}
          actions={
            <ActionGroup>
              <button
                className="btn btn-secondary btn-sm"
                onClick={(e) => handleExportHtml(e, currentCase)}
              >
                <Printer size={13} style={{ marginRight: '0.3rem' }} />
                Export HTML Dossier
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={(e) => handleExportCsv(e, currentCase)}
              >
                <FileSpreadsheet size={13} style={{ marginRight: '0.3rem' }} />
                Export Hops CSV
              </button>
            </ActionGroup>
          }
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            {/* Top Dossier KPI Overview */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '0.75rem',
                padding: '0.75rem',
                background: 'rgba(255, 255, 255, 0.02)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  Case Status
                </div>
                <div style={{ marginTop: '0.2rem' }}>
                  <StatusBadge
                    status={currentCase.status || 'OPEN'}
                    size="sm"
                  />
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  Target Identifier
                </div>
                <div style={{ marginTop: '0.2rem' }}>
                  <CopyHash
                    value={currentCase.target_id}
                    truncateLength={10}
                  />
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  Subject / Summary
                </div>
                <div
                  style={{
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: 'var(--text-main)',
                    marginTop: '0.2rem',
                  }}
                >
                  {currentCase.title || 'Automated Forensic Investigation'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  Associated Entities
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: '0.9rem',
                    fontWeight: 700,
                    color: 'var(--text-emphasis)',
                    marginTop: '0.2rem',
                  }}
                >
                  {currentCase.entities
                    ? currentCase.entities.length
                    : (currentCase.entity_count ?? 1)}
                </div>
              </div>
            </div>

            {/* Main Investigation Split: Left = Interactive Audit Timeline; Right = Associated Entities & Evidence */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                gap: '1.25rem',
              }}
            >
              {/* Left Column: Timeline & Chain of Custody */}
              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                    }}
                  >
                    <Clock size={16} style={{ color: 'var(--btc-orange)' }} />
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        color: 'var(--text-emphasis)',
                      }}
                    >
                      Audit Timeline &amp; Chain of Custody (
                      {timelineEvents.length})
                    </span>
                  </div>
                  {loadingTimeline && (
                    <span
                      style={{
                        fontSize: '0.72rem',
                        color: 'var(--text-dim)',
                      }}
                    >
                      Syncing…
                    </span>
                  )}
                </div>

                {/* Timeline Events List */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.6rem',
                    maxHeight: '340px',
                    overflowY: 'auto',
                    paddingRight: '0.4rem',
                  }}
                >
                  {timelineEvents.length > 0 ? (
                    timelineEvents.map((evt, idx) => {
                      const dt = evt.timestamp
                        ? new Date(evt.timestamp * 1000).toLocaleString()
                        : 'Recorded';
                      const details = evt.details || {};
                      const noteText =
                        details.note ||
                        details.description ||
                        evt.event_type ||
                        'Event recorded';
                      return (
                        <div
                          key={evt.event_id || idx}
                          style={{
                            padding: '0.6rem 0.8rem',
                            background: 'rgba(255, 255, 255, 0.02)',
                            borderRadius: 'var(--radius-sm)',
                            borderLeft: '3px solid var(--btc-orange)',
                            borderTop: '1px solid var(--border-subtle)',
                            borderRight: '1px solid var(--border-subtle)',
                            borderBottom: '1px solid var(--border-subtle)',
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '0.5rem',
                              marginBottom: '0.3rem',
                            }}
                          >
                            <span
                              className="badge badge-amber mono"
                              style={{ fontSize: '0.68rem' }}
                            >
                              {evt.event_type}
                            </span>
                            <span
                              className="mono"
                              style={{
                                fontSize: '0.7rem',
                                color: 'var(--text-dim)',
                              }}
                            >
                              {dt}
                            </span>
                          </div>
                          <div
                            style={{
                              fontSize: '0.8rem',
                              color: 'var(--text-main)',
                              lineHeight: 1.4,
                            }}
                          >
                            {noteText}
                          </div>
                          {details.recorded_by && (
                            <div
                              style={{
                                fontSize: '0.7rem',
                                color: 'var(--text-dim)',
                                marginTop: '0.25rem',
                              }}
                            >
                              Operator:{' '}
                              <span className="mono">
                                {details.recorded_by}
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <div
                      style={{
                        padding: '1.5rem',
                        textAlign: 'center',
                        color: 'var(--text-dim)',
                        fontSize: '0.82rem',
                      }}
                    >
                      No audit events recorded yet. Add an investigative note
                      below to establish evidentiary chain of custody.
                    </div>
                  )}
                </div>

                {/* Inline Add Timeline Event Form */}
                <form
                  onSubmit={handleAddTimelineEvent}
                  style={{
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '0.85rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        color: 'var(--text-muted)',
                      }}
                    >
                      Record Forensic Audit Note / Investigative Action
                    </span>
                    <select
                      className="input"
                      style={{
                        fontSize: '0.75rem',
                        padding: '0.2rem 0.5rem',
                        width: 'auto',
                      }}
                      value={newEventType}
                      onChange={(e) => setNewEventType(e.target.value)}
                    >
                      {EVENT_TYPE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="text"
                      className="input"
                      style={{ flex: 1, fontSize: '0.8rem' }}
                      placeholder="Add evidentiary finding, subpoena reference, or pivot reason..."
                      value={newEventText}
                      onChange={(e) => setNewEventText(e.target.value)}
                    />
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={submittingEvent || !newEventText.trim()}
                    >
                      <Send size={13} />
                      {submittingEvent ? 'Recording…' : 'Record'}
                    </button>
                  </div>
                </form>
              </div>

              {/* Right Column: Associated Entities & Evidentiary Findings */}
              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  padding: '1rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <Layers size={16} style={{ color: 'var(--color-primary)' }} />
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      color: 'var(--text-emphasis)',
                    }}
                  >
                    Evidentiary Entities &amp; Forensic Graph Context
                  </span>
                </div>

                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                    maxHeight: '340px',
                    overflowY: 'auto',
                  }}
                >
                  {currentCase.entities && currentCase.entities.length > 0 ? (
                    currentCase.entities.map((ent, idx) => {
                      const entId =
                        typeof ent === 'string' ? ent : ent.entity_id || `ENT_${idx}`;
                      return (
                        <div
                          key={entId}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '0.55rem 0.75rem',
                            background: 'rgba(255, 255, 255, 0.02)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--border-subtle)',
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.6rem',
                            }}
                          >
                            <span
                              className="mono"
                              style={{
                                fontSize: '0.8rem',
                                color: 'var(--btc-orange)',
                                fontWeight: 600,
                              }}
                            >
                              {entId}
                            </span>
                            {entId === currentCase.target_id && (
                              <span
                                className="badge badge-amber mono"
                                style={{ fontSize: '0.62rem' }}
                              >
                                TARGET
                              </span>
                            )}
                          </div>
                          <span
                            style={{
                              fontSize: '0.72rem',
                              color: 'var(--text-dim)',
                            }}
                          >
                            Graph Node #{idx + 1}
                          </span>
                        </div>
                      );
                    })
                  ) : (
                    <div
                      style={{
                        padding: '1.5rem',
                        textAlign: 'center',
                        color: 'var(--text-dim)',
                        fontSize: '0.82rem',
                      }}
                    >
                      Target entity: <strong className="mono">{currentCase.target_id}</strong>
                    </div>
                  )}
                </div>

                {/* Evidence Summary Box */}
                <div
                  style={{
                    marginTop: 'auto',
                    padding: '0.75rem',
                    background: 'rgba(247, 147, 26, 0.04)',
                    border: '1px solid rgba(247, 147, 26, 0.2)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  <div
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: 'var(--btc-orange)',
                      marginBottom: '0.2rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                    }}
                  >
                    <ShieldCheck size={14} /> Defensible Forensic Record
                  </div>
                  <div
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      lineHeight: 1.4,
                    }}
                  >
                    All timestamps, hops, and decay scores are cryptographically
                    hashed and exported in RFC-compliant formats ready for
                    judicial submission.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </SectionCard>
      )}
    </div>
  );
}
