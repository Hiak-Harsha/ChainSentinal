/**
 * ChainSentinel Forensic API Client
 * Interfaces with FastAPI offline backend on /api/
 */

const API_BASE = '/api';

// Read API key from Vite env (build-time injection) or fallback for dev
const API_KEY = typeof import.meta !== 'undefined' && import.meta.env
  ? import.meta.env.VITE_CS_API_KEY || ''
  : '';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Attach API key to all requests except health
  if (API_KEY && !endpoint.startsWith('/health')) {
    headers['X-API-Key'] = API_KEY;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const res = await fetch(url, config);

    // Surface rate limiting
    if (res.status === 429) {
      const retryAfter = res.headers.get('Retry-After') || '30';
      throw new Error(`Rate limited. Retry in ${retryAfter}s`);
    }

    // Surface auth failures
    if (res.status === 401) {
      throw new Error('Authentication failed: invalid or missing API key');
    }

    // Surface upload rejections
    if (res.status === 413) {
      throw new Error('File exceeds maximum allowed upload size');
    }

    if (res.status === 415) {
      throw new Error('Unsupported file type');
    }

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
  getCaseTimeline: (caseId) => request(`/trace/cases/${encodeURIComponent(caseId)}/timeline`),
  addCaseTimelineEvent: (caseId, event) =>
    request(`/trace/cases/${encodeURIComponent(caseId)}/timeline`, {
      method: 'POST',
      body: JSON.stringify(event),
    }),

  // AI/ML Model Lab
  getModelLab: () => request('/models/lab'),
  trainModels: () => request('/models/train', { method: 'POST', body: JSON.stringify({}) }),
  runDetection: (minRisk = 0.35, limit = 50) =>
    request('/models/detect', {
      method: 'POST',
      body: JSON.stringify({ min_risk_score: minRisk, limit }),
    }),

  // Active Learning & Timeseries
  getSimilarEntities: (entityId, topK = 5) =>
    request(`/graph/entities/${encodeURIComponent(entityId)}/similar?top_k=${topK}`),
  submitAlertFeedback: (alertId, verdict, notes = '') =>
    request(`/alerts/${encodeURIComponent(alertId)}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ verdict, notes }),
    }),
  getAlertFeedback: (limit = 50) => request(`/alerts/feedback/list?limit=${limit}`),
  getAlertTimeseries: (bucket = 'hour') => request(`/alerts/timeseries?bucket=${bucket}`),

  // Ingestion & Schema Wizard
  getIngestJobs: () => request('/ingest/jobs'),
  getIngestProfiles: () => request('/ingest/profiles'),

  // Background Jobs
  startJob: (endpoint, body = {}) =>
    request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getJobStatus: (jobId) => request(`/jobs/${encodeURIComponent(jobId)}`),
};

