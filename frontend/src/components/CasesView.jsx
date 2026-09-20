import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  FileText,
  Download,
  Printer,
  PlusCircle,
  CheckCircle2,
  Lock,
  FolderOpen,
} from 'lucide-react';
import { api } from '../api';
import { CopyHash, StatusBadge, useToast } from './shared';

export default function CasesView({ prefilledTarget = '' }) {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [loading, setLoading] = useState(false);

  // New investigation input
  const [newTarget, setNewTarget] = useState(prefilledTarget || '');
  const [investigating, setInvestigating] = useState(false);
  const toast = useToast();

  const loadCases = async () => {
    setLoading(true);
    try {
      const data = await api.getCases();
      setCases(data || []);
      if (data && data.length > 0 && !selectedCase) {
        setSelectedCase(data[0].case_data || data[0]);
      }
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
      setSelectedCase(newCase);
      await loadCases();
      toast?.showToast(`Investigation dossier ${newCase.case_id || ''} sealed and archived`, 'success');
    } catch (err) {
      toast?.showToast(`Investigation failed: ${err.message}`, 'error');
    } finally {
      setInvestigating(false);
    }
  };

  const handleExportJSON = (caseObj) => {
    if (!caseObj) return;
    const blob = new Blob([JSON.stringify(caseObj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${caseObj.case_id || 'case_file'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast?.showToast(`Exported ${caseObj.case_id || 'case'}.json evidence bundle`, 'info');
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Header & Launch Bar */}
      <div
        className="card"
        style={{
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <FileText size={22} style={{ color: 'var(--cyan-primary)' }} />
            Autonomous Forensic Case Dossiers
          </h2>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '0.2rem' }}>
            Court-admissible case files generated autonomously with bidirectional taint tracking, IP attribution, and SHA-256 evidence digests.
          </div>
        </div>

        {/* Launch New Case */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
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

      {/* Main Grid: Cases Directory + Dossier Reader */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.5rem' }}>
        {/* Left: Case Directory List */}
        <div className="card" style={{ height: '700px', display: 'flex', flexDirection: 'column' }}>
          <div className="card-header">
            <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FolderOpen size={16} style={{ color: 'var(--cyan-primary)' }} />
              Directory ({cases.length})
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {cases.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '2rem' }}>
                No case files generated yet.
              </div>
            ) : (
              cases.map((c) => {
                const cData = c.case_data || c;
                const isSelected = selectedCase?.case_id === cData.case_id;
                return (
                  <motion.div
                    key={c.case_id}
                    onClick={() => setSelectedCase(cData)}
                    whileHover={{ scale: 1.01 }}
                    transition={{ duration: 0.15 }}
                    style={{
                      padding: '0.85rem',
                      borderRadius: 'var(--radius-md)',
                      background: isSelected ? 'rgba(0, 240, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                      border: `1px solid ${isSelected ? 'rgba(0, 240, 255, 0.35)' : 'var(--border-subtle)'}`,
                      cursor: 'pointer',
                      boxShadow: isSelected ? '0 0 15px rgba(0, 240, 255, 0.1)' : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <span className="mono" style={{ fontWeight: 700, fontSize: '0.8rem', color: isSelected ? 'var(--cyan-primary)' : '#fff' }}>
                        {cData.case_id}
                      </span>
                      <StatusBadge status={cData.status || 'OPEN'} size="sm" />
                    </div>

                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.3rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {cData.title}
                    </div>

                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Target: <CopyHash value={cData.target_id} label="Target" truncateLength={6} />
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Dossier Content Viewer */}
        {selectedCase ? (
          <div className="card" style={{ height: '700px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {/* Dossier Header Bar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid var(--border-subtle)',
                paddingBottom: '1rem',
                marginBottom: '1.25rem',
                flexWrap: 'wrap',
                gap: '0.75rem',
              }}
            >
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '0.2rem', fontWeight: 700 }}>
                  {selectedCase.title}
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.3rem' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Case ID:</span>
                  <CopyHash value={selectedCase.case_id} label="Case ID" />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>&bull; Target:</span>
                  <CopyHash value={selectedCase.target_id} label="Target ID" />
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleExportJSON(selectedCase)}
                  title="Download JSON Evidence Bundle"
                >
                  <Download size={14} />
                  Export JSON
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => window.print()}
                  title="Print Dossier"
                >
                  <Printer size={14} />
                  Print
                </button>
              </div>
            </div>

            {/* SHA-256 Tamper-Evident Evidence Bar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.65rem 1rem',
                background: 'rgba(0, 0, 0, 0.4)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid rgba(0, 240, 255, 0.2)',
                marginBottom: '1.25rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem' }}>
                <CheckCircle2 size={15} style={{ color: 'var(--emerald)' }} />
                <span style={{ color: 'var(--text-dim)' }}>SHA-256 Tamper-Evident Evidence Digest:</span>
              </div>

              <CopyHash
                value={selectedCase.bundle_hash || 'SHA256-DIGEST-PENDING'}
                label="Bundle Digest"
                truncateLength={12}
              />
            </div>

            {/* Markdown Narrative Report with Forensic Framing */}
            <div
              style={{
                flex: 1,
                background: 'rgba(255, 255, 255, 0.015)',
                padding: '1.5rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
                lineHeight: 1.6,
                fontSize: '0.88rem',
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--cyan-primary)', fontSize: '0.72rem', letterSpacing: '0.08em', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.5rem' }}>
                <Lock size={12} />
                CONFIDENTIAL FORENSIC DOSSIER &bull; CLASSIFIED LAW ENFORCEMENT EXHIBIT
              </div>
              <pre
                style={{
                  whiteSpace: 'pre-wrap',
                  wordWrap: 'break-word',
                  fontFamily: 'inherit',
                  margin: 0,
                  color: 'var(--text-main)',
                }}
              >
                {selectedCase.narrative_report}
              </pre>
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)' }}>
            Select a case file to view full forensic dossier.
          </div>
        )}
      </div>
    </div>
  );
}
