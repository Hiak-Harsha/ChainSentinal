import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  PlusCircle,
  FolderOpen,
  Printer,
  FileSpreadsheet,
  Calendar,
  Layers,
  Search,
} from 'lucide-react';
import { api } from '../api';
import { CopyHash, StatusBadge, useToast } from './shared';
import { SealedDossierIcon } from './visuals/icons';

export default function CasesView({
  prefilledTarget = '',
  onSelectCase,
  selectedCaseId = null,
}) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // New investigation input
  const [newTarget, setNewTarget] = useState(prefilledTarget || '');
  const [investigating, setInvestigating] = useState(false);
  const toast = useToast();

  const loadCases = async () => {
    setLoading(true);
    try {
      const data = await api.getCases();
      setCases(data || []);
    } catch (err) {
      console.error('Failed to fetch cases:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleLaunchInvestigate = async () => {
    if (!newTarget) return;
    setInvestigating(true);
    toast?.showToast(`Initiating autonomous dossier compilation for ${newTarget.slice(0, 10)}...`, 'info');
    try {
      const newCase = await api.investigate({
        target: newTarget.trim(),
        max_hops: 4,
        decay_model: 'proportional',
      });
      await loadCases();
      if (onSelectCase) onSelectCase(newCase);
      toast?.showToast(`Investigation dossier ${newCase.case_id || ''} sealed and archived`, 'success');
      setNewTarget('');
    } catch (err) {
      toast?.showToast(`Investigation failed: ${err.message}`, 'error');
    } finally {
      setInvestigating(false);
    }
  };

  const handleExportHtml = async (e, caseObj) => {
    e.stopPropagation();
    const cData = caseObj.case_data || caseObj;
    const caseId = cData.case_id;
    if (!caseId) return;
    try {
      toast?.showToast(`Opening HTML forensic dossier for ${caseId}...`, 'info');
      await api.exportCaseHtml(caseId);
    } catch (err) {
      toast?.showToast(`Export dossier failed: ${err.message}`, 'error');
    }
  };

  const handleExportCsv = async (e, caseObj) => {
    e.stopPropagation();
    const cData = caseObj.case_data || caseObj;
    const caseId = cData.case_id;
    if (!caseId) return;
    try {
      toast?.showToast(`Downloading hops CSV for ${caseId}...`, 'info');
      await api.exportCaseCsv(caseId);
      toast?.showToast(`Downloaded ${caseId}_hops.csv`, 'success');
    } catch (err) {
      toast?.showToast(`Export hops CSV failed: ${err.message}`, 'error');
    }
  };

  const filteredCases = cases.filter((c) => {
    const cData = c.case_data || c;
    const q = searchTerm.toLowerCase();
    return (
      !searchTerm ||
      cData.case_id?.toLowerCase().includes(q) ||
      cData.target_id?.toLowerCase().includes(q) ||
      cData.title?.toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      {/* Header & Launch Bar */}
      <div
        className="card"
        style={{
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-emphasis)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <FileText size={20} style={{ color: 'var(--text-main)' }} />
            Autonomous Forensic Case Dossiers
          </h2>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.2rem' }}>
            Court-admissible case files &bull; Select any case to inspect timeline &amp; chain of custody in the Inspector Panel
          </div>
        </div>

        {/* Launch New Case */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          <input
            type="text"
            className="input mono"
            style={{ width: '220px' }}
            placeholder="Entity ID / Address..."
            value={newTarget}
            onChange={(e) => setNewTarget(e.target.value)}
          />
          <button
            className="btn btn-primary"
            onClick={handleLaunchInvestigate}
            disabled={investigating || !newTarget}
          >
            <PlusCircle size={15} />
            {investigating ? 'Investigating...' : 'Generate Case'}
          </button>
        </div>
      </div>

      {/* Case Directory (Full Width Table) */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <FolderOpen size={16} style={{ color: 'var(--text-main)' }} />
            Case Directory ({filteredCases.length})
          </div>

          <div style={{ position: 'relative', minWidth: '240px' }}>
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
              style={{ width: '100%', paddingLeft: '2rem', fontSize: '0.78rem' }}
              placeholder="Search case dossiers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '50px' }}>Seal</th>
                <th>Case ID</th>
                <th>Target Entity</th>
                <th>Title / Subject</th>
                <th>Entities</th>
                <th>Events</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 'var(--space-6) var(--space-4)' }}>
                    {loading ? 'Loading case dossiers...' : 'No case files found. Enter an entity above to generate one.'}
                  </td>
                </tr>
              ) : (
                filteredCases.map((c) => {
                  const cData = c.case_data || c;
                  const isSelected = selectedCaseId === cData.case_id;
                  const isVerified = cData.status === 'RESOLVED' || cData.status === 'SEALED';
                  const entityCount = cData.entities ? cData.entities.length : (cData.entity_count ?? 1);
                  const eventCount = cData.timeline ? cData.timeline.length : (cData.events_count ?? 0);

                  return (
                    <tr
                      key={cData.case_id}
                      onClick={() => onSelectCase && onSelectCase(cData)}
                      style={{
                        cursor: 'pointer',
                        background: isSelected ? 'var(--bg-elevated)' : undefined,
                      }}
                    >
                      <td>
                        <SealedDossierIcon size={20} verified={isVerified} />
                      </td>
                      <td>
                        <span className="mono" style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-emphasis)' }}>
                          {cData.case_id}
                        </span>
                      </td>
                      <td>
                        <CopyHash value={cData.target_id} label="Target" truncateLength={6} />
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.82rem' }}>
                          {cData.title || `Forensic Dossier ${cData.case_id}`}
                        </span>
                      </td>
                      <td>
                        <span className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {entityCount}
                        </span>
                      </td>
                      <td>
                        <span className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {eventCount}
                        </span>
                      </td>
                      <td>
                        <StatusBadge status={cData.status || 'OPEN'} size="sm" />
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onSelectCase) onSelectCase(cData);
                            }}
                          >
                            Inspect
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={(e) => handleExportHtml(e, cData)}
                            title="Export Dossier (HTML/Print)"
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
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
