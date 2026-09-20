import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Cpu,
  RefreshCw,
  BarChart3,
  Flame,
  Zap,
} from 'lucide-react';
import { api } from '../api';
import { AnimatedNumber, Skeleton, StatusBadge, useToast } from './shared';

export default function ModelLabView({ onTriggerDetect }) {
  const [labData, setLabData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const toast = useToast();

  const loadLab = async () => {
    setLoading(true);
    try {
      const data = await api.getModelLab();
      setLabData(data);
    } catch (err) {
      console.error('Failed to load model lab diagnostics:', err);
      toast?.showToast('Failed to load model lab diagnostics', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLab();
  }, []);

  const handleRetrain = async () => {
    setTraining(true);
    toast?.showToast('Retraining supervised & unsupervised models with cross-validation...', 'info');
    try {
      await api.trainModels();
      await loadLab();
      toast?.showToast('Model training complete: weights, calibrations, and TreeSHAP updated', 'success');
    } catch (err) {
      toast?.showToast(`Retraining failed: ${err.message}`, 'error');
    } finally {
      setTraining(false);
    }
  };

  const supervisedMetrics = labData?.supervised_metrics ?? null;
  const holdoutResults = labData?.holdout_experiment ?? null;
  const featureImportances = labData?.feature_importances ?? [];

  return (
    <div style={{ position: 'relative' }}>
      {/* Action Header */}
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
            <Cpu size={22} style={{ color: 'var(--cyan-primary)' }} />
            AI/ML Intelligence Laboratory
          </h2>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: '0.2rem' }}>
            Model diagnostics, conformal coverage calibrations, and unseen holdout anomaly evaluation.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            className="btn btn-secondary"
            onClick={loadLab}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh Lab
          </button>
          <button
            className="btn btn-primary"
            onClick={handleRetrain}
            disabled={training}
          >
            <Zap size={14} />
            {training ? 'Training Estimators...' : 'Retrain All Models'}
          </button>
        </div>
      </div>

      {/* KPI Row: Supervised Accuracy, F1, Conformal Coverage */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card kpi-card cyan">
          <div className="kpi-top">
            <span>Typology Accuracy</span>
          </div>
          <div className="kpi-value mono" style={{ color: 'var(--cyan-primary)' }}>
            {supervisedMetrics?.accuracy !== undefined ? (
              <AnimatedNumber value={supervisedMetrics.accuracy * 100} decimals={1} suffix="%" />
            ) : loading ? (
              <Skeleton width="80px" height="2rem" />
            ) : (
              '—'
            )}
          </div>
          <div className="kpi-meta">
            HistGradientBoosting Multi-Class
          </div>
        </div>

        <div className="card kpi-card emerald">
          <div className="kpi-top">
            <span>F1 Macro Score</span>
          </div>
          <div className="kpi-value mono" style={{ color: 'var(--emerald)' }}>
            {supervisedMetrics?.f1_macro !== undefined ? (
              <AnimatedNumber value={supervisedMetrics.f1_macro * 100} decimals={1} suffix="%" />
            ) : loading ? (
              <Skeleton width="80px" height="2rem" />
            ) : (
              '—'
            )}
          </div>
          <div className="kpi-meta">
            Balanced across T1–T9 Typologies
          </div>
        </div>

        <div className="card kpi-card purple">
          <div className="kpi-top">
            <span>Conformal Coverage</span>
          </div>
          <div className="kpi-value mono" style={{ color: 'var(--purple-primary)' }}>
            {labData?.conformal?.coverage !== undefined ? (
              <AnimatedNumber value={labData.conformal.coverage * 100} decimals={1} suffix="%" />
            ) : (
              '90.0% Target'
            )}
          </div>
          <div className="kpi-meta">
            Inductive Split Conformal Guarantee
          </div>
        </div>

        <div className="card kpi-card crimson">
          <div className="kpi-top">
            <span>Unseen Anomaly Catch</span>
          </div>
          <div className="kpi-value mono" style={{ color: 'var(--crimson)' }}>
            {holdoutResults?.flagged_as_anomalous_ratio !== undefined ? (
              <AnimatedNumber value={holdoutResults.flagged_as_anomalous_ratio * 100} decimals={1} suffix="%" />
            ) : loading ? (
              <Skeleton width="80px" height="2rem" />
            ) : (
              '—'
            )}
          </div>
          <div className="kpi-meta">
            Hold-out Typology Detection Rate
          </div>
        </div>
      </div>

      {/* Two-Column Grid: Holdout Experiment (Proof of Real AI) + Global Feature Importance */}
      <div className="grid-2">
        {/* Left: Unseen Typology Experiment Card */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <Flame size={18} style={{ color: 'var(--amber)' }} />
                Unseen Hold-Out Typology Experiment
              </div>
              <div className="card-subtitle">
                Proof of Real Machine Learning — Detecting Unseen Patterns Without Labels
              </div>
            </div>
            <StatusBadge
              status={holdoutResults ? 'RESOLVED' : 'INVESTIGATING'}
              size="sm"
            />
          </div>

          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '1.25rem' }}>
            The NTRO problem statement explicitly demands <em>"real AI/ML, not just hardcoded rules"</em>.
            To prove inductive generalization, our unsupervised Isolation Forest model is evaluated strictly <strong>without</strong> hold-out typologies <code>T8 (Dusting Attack)</code> and <code>T9 (Multi-Cluster Operator)</code>.
          </div>

          {/* Anomaly Separation Bar */}
          {holdoutResults ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Legitimate Baseline Anomaly Score:</span>
                  <span className="mono" style={{ color: 'var(--emerald)', fontWeight: 700 }}>
                    {holdoutResults.legitimate_anomaly_mean.toFixed(3)}
                  </span>
                </div>
                <div style={{ height: '8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, Math.max(0, holdoutResults.legitimate_anomaly_mean * 100))}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    style={{
                      height: '100%',
                      background: 'var(--emerald)',
                      boxShadow: '0 0 8px var(--emerald)',
                    }}
                  />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                  <span style={{ color: 'var(--text-dim)' }}>Unseen Hold-Out Anomaly Score:</span>
                  <span className="mono" style={{ color: 'var(--crimson)', fontWeight: 700 }}>
                    {holdoutResults.holdout_anomaly_mean.toFixed(3)}
                  </span>
                </div>
                <div style={{ height: '8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, Math.max(0, holdoutResults.holdout_anomaly_mean * 100))}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    style={{
                      height: '100%',
                      background: 'var(--crimson)',
                      boxShadow: '0 0 8px var(--crimson)',
                    }}
                  />
                </div>
              </div>

              <div
                style={{
                  marginTop: '0.5rem',
                  padding: '0.85rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(0, 240, 255, 0.04)',
                  border: '1px solid rgba(0, 240, 255, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span style={{ fontSize: '0.82rem', color: 'var(--text-main)', fontWeight: 600 }}>
                  Empirical Separation Delta (&Delta;):
                </span>
                <span className="mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--cyan-primary)' }}>
                  {holdoutResults.anomaly_separation_delta >= 0 ? `+${holdoutResults.anomaly_separation_delta.toFixed(3)}` : holdoutResults.anomaly_separation_delta.toFixed(3)}
                </span>
              </div>
            </div>
          ) : (
            <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
              No hold-out experiment metrics available. Click &quot;Retrain All Models&quot; to evaluate.
            </div>
          )}
        </div>

        {/* Right: Global TreeSHAP Feature Importance */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <BarChart3 size={18} style={{ color: 'var(--cyan-primary)' }} />
                Global Feature Importance Rankings
              </div>
              <div className="card-subtitle">
                Top multimodal forensic discriminators isolated across 35 features
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {featureImportances.length === 0 ? (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
                No feature importance data available. Trigger training to compute TreeSHAP attributions.
              </div>
            ) : (
              featureImportances.map((item, idx) => {
                const pct = Math.min(100, Math.round((item.importance / 0.2) * 100));
                return (
                  <div key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                      <span className="mono" style={{ color: 'var(--text-muted)' }}>
                        {item.feature.replace(/_/g, ' ')}
                      </span>
                      <span className="mono" style={{ color: 'var(--cyan-primary)', fontWeight: 600 }}>
                        {(item.importance * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div style={{ height: '7px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.5, delay: idx * 0.04 }}
                        style={{
                          height: '100%',
                          background: 'linear-gradient(90deg, #00f0ff, #3b82f6)',
                          boxShadow: '0 0 6px rgba(0, 240, 255, 0.4)',
                        }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
