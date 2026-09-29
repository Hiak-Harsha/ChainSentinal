/**
 * ChainSentinel Forensic API Client
 * Interfaces with FastAPI offline backend on /api/
 */

const API_BASE = '/api';

// Read API key from localStorage, window global, or Vite env
export function getApiKey() {
  if (typeof window !== 'undefined' && window.__CS_API_KEY__) return window.__CS_API_KEY__;
  if (typeof localStorage !== 'undefined') {
    const stored = localStorage.getItem('chainsentinel_api_key');
    if (stored) return stored;
  }
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_CS_API_KEY) {
    return import.meta.env.VITE_CS_API_KEY;
  }
  return '';
}

/**
 * Format error details cleanly for operator presentation.
 */
function formatErrorDetail(detail, status) {
  if (!detail) return `HTTP Error ${status}`;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = item.loc ? item.loc[item.loc.length - 1] : 'field';
        return `${field}: ${item.msg || 'invalid'}`;
      })
      .join('; ');
  }
  if (typeof detail === 'object') {
    return detail.message || JSON.stringify(detail);
  }
  return String(detail);
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Attach API key to all requests except health
  const apiKey = getApiKey();
  if (apiKey && !endpoint.startsWith('/health')) {
    headers['X-API-Key'] = apiKey;
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
      throw new Error('Authentication failed: invalid or missing API key.');
    }

    if (res.status === 403) {
      throw new Error('Access denied: insufficient investigative permissions.');
    }

    // Surface upload rejections
    if (res.status === 413) {
      throw new Error('File exceeds maximum allowed upload size (limit: 50MB).');
    }

    if (res.status === 415) {
      throw new Error('Unsupported file type. Accepted formats: CSV, JSON, XML.');
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(formatErrorDetail(errData.detail, res.status));
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      // Re-throw AbortError untouched so callers can detect cancellation
      throw err;
    }
    if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
      throw new Error('Unable to connect to ChainSentinel backend server. Verify the service is online.');
    }
    console.error(`API Error [${endpoint}]:`, err);
    throw err;
  }
}

export const api = {
  // System Health
  getHealth: (options = {}) => request('/health', options),

  // Alerts & Triage (Section 7 NTRO Contract)
  getAlerts: (params = {}, options = {}) => {
    const query = new URLSearchParams();
    if (params.min_priority !== undefined) query.set('min_priority', params.min_priority);
    if (params.min_risk !== undefined) query.set('min_risk', params.min_risk);
    if (params.status) query.set('status', params.status);
    if (params.limit) query.set('limit', params.limit);
    if (params.offset) query.set('offset', params.offset);
    return request(`/alerts?${query.toString()}`, options);
  },
  getAlertDetail: (alertId, options = {}) =>
    request(`/alerts/${encodeURIComponent(alertId)}`, options),
  updateAlertStatus: (alertId, status, options = {}) =>
    request(`/alerts/${encodeURIComponent(alertId)}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
      ...options,
    }),

  // Graph & Entity Explorer
  getEntities: (params = 100, options = {}) => {
    if (typeof params === 'number') {
      return request(`/graph/entities?limit=${params}`, options);
    }
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set('limit', params.limit);
    if (params.offset !== undefined) query.set('offset', params.offset);
    if (params.entity_type) query.set('entity_type', params.entity_type);
    if (params.search) query.set('search', params.search);
    return request(`/graph/entities?${query.toString()}`, options);
  },
  getEntityDetail: (entityId, options = {}) =>
    request(`/graph/entities/${encodeURIComponent(entityId)}`, options),
  getEgoSubgraph: (centerId, hops = 2, options = {}) =>
    request(
      `/graph/subgraph?center_id=${encodeURIComponent(centerId)}&hops=${hops}`,
      options
    ),
  getGraphMetrics: (options = {}) => request('/graph/metrics', options),
  getGraphStats: (options = {}) => request('/graph/stats', options),

  // Correlation & Network Attribution
  getOperatorLinks: (maxPValue = 0.05, options = {}) =>
    request(`/correlate/operator-links?max_p_value=${maxPValue}`, options),
  getEntitySignatures: (entityId, options = {}) =>
    request(`/correlate/signatures/${encodeURIComponent(entityId)}`, options),

  // Taint Tracing & Pathfinder
  runTrace: (params, options = {}) =>
    request('/trace/run', {
      method: 'POST',
      body: JSON.stringify(params),
      ...options,
    }),
  getTrace: (traceId, options = {}) => request(`/trace/${encodeURIComponent(traceId)}`, options),
  listTraces: (options = {}) => request('/trace/history', options),
  computePath: (params, options = {}) =>
    request('/trace/path', {
      method: 'POST',
      body: JSON.stringify(params),
      ...options,
    }),

  // Autonomous Investigation & Case Files
  investigate: (params, options = {}) =>
    request('/trace/investigate', {
      method: 'POST',
      body: JSON.stringify(params),
      ...options,
    }),
  getCases: (options = {}) => request('/trace/cases', options),
  getCaseFile: (caseId, options = {}) =>
    request(`/trace/cases/${encodeURIComponent(caseId)}`, options),
  getCaseTimeline: (caseId, options = {}) =>
    request(`/trace/cases/${encodeURIComponent(caseId)}/timeline`, options),
  addCaseTimelineEvent: (caseId, event, options = {}) =>
    request(`/trace/cases/${encodeURIComponent(caseId)}/timeline`, {
      method: 'POST',
      body: JSON.stringify(event),
      ...options,
    }),
  exportCaseHtml: async (caseId) => {
    const url = `${API_BASE}/trace/cases/${encodeURIComponent(caseId)}/export/html`;
    const apiKey = getApiKey();
    if (apiKey) headers['X-API-Key'] = apiKey;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(`Export HTML failed: ${res.statusText}`);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    window.open(objectUrl, '_blank');
  },
  exportCaseCsv: async (caseId) => {
    const url = `${API_BASE}/trace/cases/${encodeURIComponent(caseId)}/export/csv`;
    const apiKey = getApiKey();
    if (apiKey) headers['X-API-Key'] = apiKey;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(`Export CSV failed: ${res.statusText}`);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = `${caseId}_hops.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(objectUrl);
  },

  // AI/ML Model Lab
  getModelLab: (options = {}) => request('/models/lab', options),
  trainModels: (asyncMode = false, options = {}) =>
    request(`/models/train${asyncMode ? '?async=true' : ''}`, {
      method: 'POST',
      body: JSON.stringify(asyncMode ? { async_mode: true } : {}),
      ...options,
    }),
  runDetection: (minRisk = 0.35, limit = 50, options = {}) =>
    request('/models/detect', {
      method: 'POST',
      body: JSON.stringify({ min_risk_score: minRisk, limit }),
      ...options,
    }),

  // Active Learning & Timeseries
  getSimilarEntities: (entityId, topK = 5, options = {}) =>
    request(`/graph/entities/${encodeURIComponent(entityId)}/similar?top_k=${topK}`, options),
  submitAlertFeedback: (alertId, verdict, notes = '', options = {}) =>
    request(`/alerts/${encodeURIComponent(alertId)}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ verdict, notes }),
      ...options,
    }),
  getAlertFeedback: (limit = 50, options = {}) =>
    request(`/alerts/feedback/list?limit=${limit}`, options),
  getAlertTimeseries: (bucket = 'hour', options = {}) =>
    request(`/alerts/timeseries?bucket=${bucket}`, options),

  // Ingestion & Schema Wizard
  getIngestJobs: (options = {}) => request('/ingest/jobs', options),
  getIngestJob: (jobId, options = {}) =>
    request(`/ingest/jobs/${encodeURIComponent(jobId)}`, options),
  getIngestQC: (jobId, options = {}) =>
    request(`/ingest/jobs/${encodeURIComponent(jobId)}/qc-report`, options),
  getQuarantine: (params = {}, options = {}) => {
    const query = new URLSearchParams();
    if (params.limit) query.set('limit', params.limit);
    if (params.offset) query.set('offset', params.offset);
    if (params.reason_code) query.set('reason_code', params.reason_code);
    return request(`/ingest/quarantine?${query.toString()}`, options);
  },
  detectSchema: async (fileOrDataset, options = {}) => {
    if (typeof fileOrDataset === 'string') {
      return request('/ingest/detect-schema', {
        method: 'POST',
        body: JSON.stringify({ dataset_name: fileOrDataset }),
        ...options,
      });
    }
    const form = new FormData();
    form.append('file', fileOrDataset);
    const res = await fetch(`${API_BASE}/ingest/detect-schema`, {
      method: 'POST',
      body: form,
      signal: options.signal,
      ...(getApiKey() ? { headers: { 'X-API-Key': getApiKey() } } : {}),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Schema detection failed: HTTP ${res.status}`);
    }
    return res.json();
  },
  uploadIngest: async (file, profileName = '', options = {}) => {
    const form = new FormData();
    form.append('file', file);
    const query = profileName ? `?profile_name=${encodeURIComponent(profileName)}` : '';
    const res = await fetch(`${API_BASE}/ingest/upload${query}`, {
      method: 'POST',
      body: form,
      signal: options.signal,
      ...(getApiKey() ? { headers: { 'X-API-Key': getApiKey() } } : {}),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Upload failed: HTTP ${res.status}`);
    }
    return res.json();
  },
  getIngestProfiles: (options = {}) => request('/ingest/profiles', options),

  // Background Jobs
  startJob: (endpoint, body = {}, options = {}) =>
    request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
      ...options,
    }),
  getJobStatus: (jobId, options = {}) =>
    request(`/jobs/${encodeURIComponent(jobId)}`, options),
};
