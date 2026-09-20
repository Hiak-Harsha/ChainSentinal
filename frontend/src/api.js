/**
 * ChainSentinel Forensic API Client
 * Interfaces with FastAPI offline backend on /api/
 */

const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || `HTTP Error ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error [${endpoint}]:`, err);
    throw err;
  }
}

export const api = {
  // System Health
  getHealth: () => request('/health'),

  // Alerts & Triage (Section 7 NTRO Contract)
  getAlerts: (params = {}) => {
    const query = new URLSearchParams();
    if (params.min_priority !== undefined) query.set('min_priority', params.min_priority);
    if (params.min_risk !== undefined) query.set('min_risk', params.min_risk);
    if (params.status) query.set('status', params.status);
    if (params.limit) query.set('limit', params.limit);
    return request(`/alerts?${query.toString()}`);
  },
  getAlertDetail: (alertId) => request(`/alerts/${encodeURIComponent(alertId)}`),
  updateAlertStatus: (alertId, status) =>
    request(`/alerts/${encodeURIComponent(alertId)}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),

  // Graph & Entity Explorer
  getEntities: (limit = 100) => request(`/graph/entities?limit=${limit}`),
  getEntityDetail: (entityId) => request(`/graph/entities/${encodeURIComponent(entityId)}`),
  getEgoSubgraph: (centerId, hops = 2) =>
    request(`/graph/subgraph?center_id=${encodeURIComponent(centerId)}&hops=${hops}`),
  getGraphMetrics: () => request('/graph/metrics'),

  // Correlation & Network Attribution
  getOperatorLinks: (maxPValue = 0.05) =>
    request(`/correlate/operator-links?max_p_value=${maxPValue}`),
  getEntitySignatures: (entityId) =>
    request(`/correlate/signatures/${encodeURIComponent(entityId)}`),

  // Taint Tracing & Pathfinder
  runTrace: (params) =>
    request('/trace/run', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  getTrace: (traceId) => request(`/trace/${encodeURIComponent(traceId)}`),
  listTraces: () => request('/trace/history'),
  computePath: (params) =>
    request('/trace/path', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  // Autonomous Investigation & Case Files
  investigate: (params) =>
    request('/trace/investigate', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  getCases: () => request('/trace/cases'),
  getCaseFile: (caseId) => request(`/trace/cases/${encodeURIComponent(caseId)}`),

  // AI/ML Model Lab
  getModelLab: () => request('/models/lab'),
  trainModels: () => request('/models/train', { method: 'POST', body: JSON.stringify({}) }),
  runDetection: (minRisk = 0.35, limit = 50) =>
    request('/models/detect', {
      method: 'POST',
      body: JSON.stringify({ min_risk_score: minRisk, limit }),
    }),

  // Ingestion & Schema Wizard
  getIngestJobs: () => request('/ingest/jobs'),
  getIngestProfiles: () => request('/ingest/profiles'),
};
