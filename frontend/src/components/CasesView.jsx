import React, { useEffect, useState } from 'react';
import {
  FileText,
  ShieldAlert,
  Copy,
  Check,
  Download,
  Printer,
  PlusCircle,
  ExternalLink,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../api';

export default function CasesView({ prefilledTarget = '' }) {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // New investigation input
  const [newTarget, setNewTarget] = useState(prefilledTarget || '');
  const [investigating, setInvestigating] = useState(false);

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
    try {
      const newCase = await api.investigate({
        target: newTarget.trim(),
        max_hops: 4,
        decay_model: 'proportional',
      });
      setSelectedCase(newCase);
      await loadCases();
    } catch (err) {
      alert(`Autonomous investigation failed: ${err.message}`);
    } finally {
      setInvestigating(false);
    }
  };

  const handleCopyHash = (hash) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
  };

  return (
    <div>
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
            <div className="card-title">
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
                  <div
                    key={c.case_id}
                    onClick={() => setSelectedCase(cData)}
                    style={{
                      padding: '0.85rem',
                      borderRadius: 'var(--radius-md)',
                      background: isSelected ? 'rgba(0, 242, 254, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                      border: `1px solid ${isSelected ? 'rgba(0, 242, 254, 0.3)' : 'var(--border-subtle)'}`,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                      <span className="mono" style={{ fontWeight: 700, fontSize: '0.8rem', color: isSelected ? 'var(--cyan-primary)' : '#fff' }}>
                        {cData.case_id}
                      </span>
                      <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                        {cData.status || 'OPEN'}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.3rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {cData.title}
                    </div>

                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                      Target: <span className="mono">{cData.target_id}</span>
                    </div>
                  </div>
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
                <h3 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '0.2rem' }}>
                  {selectedCase.title}
                </h3>
                <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  Case ID: {selectedCase.case_id} &bull; Target: {selectedCase.target_id}
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
                border: '1px solid var(--border-subtle)',
                marginBottom: '1.25rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem' }}>
                <CheckCircle2 size={15} style={{ color: 'var(--emerald)' }} />
                <span style={{ color: 'var(--text-dim)' }}>SHA-256 Evidence Bundle Digest:</span>
                <span className="mono" style={{ color: 'var(--cyan-primary)', fontSize: '0.78rem' }}>
                  {selectedCase.bundle_hash}
                </span>
              </div>

              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleCopyHash(selectedCase.bundle_hash)}
              >
                {copied ? <Check size={13} style={{ color: 'var(--emerald)' }} /> : <Copy size={13} />}
              </button>
            </div>

            {/* Markdown Narrative Report */}
            <div
              style={{
                flex: 1,
                background: 'rgba(255, 255, 255, 0.01)',
                padding: '1.5rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                lineHeight: 1.6,
                fontSize: '0.9rem',
              }}
            >
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
