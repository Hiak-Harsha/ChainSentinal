/**
 * ChainSentinel Forensic API Client
 * Enterprise-grade unified API layer with HttpOnly session support,
 * configurable base URL, error normalization, AbortController support, and timeouts.
 */

// Determine API Base URL safely:
// 1. If VITE_API_URL is configured (e.g. split frontend-backend deployment), use it.
// 2. Otherwise default to same-origin '/api'
export const getApiBase = () => {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) {
    const raw = import.meta.env.VITE_API_URL.replace(/\/+$/, '');
    return raw.endsWith('/api') ? raw : `${raw}/api`;
  }
  return '/api';
};

export const API_BASE = getApiBase();

/**
 * Construct secure WebSocket URL for live forensic intelligence events.
 * Automatically selects wss:// on HTTPS and respects VITE_WS_URL or API_BASE host.
 */
export const getWsUrl = () => {
  if (typeof window === 'undefined') return '';
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }
  if (API_BASE.startsWith('http://') || API_BASE.startsWith('https://')) {
    const u = new URL(API_BASE);
    const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProto}//${u.host}/ws/live`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/live`;
};

export const DEFAULT_API_KEY = 'I59XOhtSA971eQQJ2YZrsaPGvQysvoc8KXQROOvCSMg';

let activeSessionToken = null;

export function getSessionToken() {
  if (activeSessionToken) return activeSessionToken;
  if (typeof sessionStorage !== 'undefined') {
    return sessionStorage.getItem('cs_session_token') || '';
  }
  return '';
}

export function setSessionToken(token) {
  activeSessionToken = token || null;
  if (typeof sessionStorage !== 'undefined') {
    if (token) {
      sessionStorage.setItem('cs_session_token', token);
    } else {
      sessionStorage.removeItem('cs_session_token');
    }
  }
}

export function setApiKey(key) {
  if (typeof localStorage !== 'undefined') {
    if (key) {
      localStorage.setItem('chainsentinel_api_key', key);
    } else {
      localStorage.removeItem('chainsentinel_api_key');
    }
  }
}

/**
 * Read API key if explicitly provided for headless or test environments.
 * Falls back to localStorage, VITE_API_KEY environment variable, or the
 * configured server default key.
 */
export function getApiKey() {
  if (typeof window !== 'undefined' && window.__CS_API_KEY__) return window.__CS_API_KEY__;
  if (typeof localStorage !== 'undefined') {
    const stored = localStorage.getItem('chainsentinel_api_key');
    if (stored) return stored;
  }
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_KEY) {
    return import.meta.env.VITE_API_KEY;
  }
  return DEFAULT_API_KEY;
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

/**
 * Core unified request dispatcher.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...options.headers,
  };

  // Attach API key
  const apiKey = getApiKey();
  if (apiKey && !headers['X-API-Key']) {
    headers['X-API-Key'] = apiKey;
  }

  // Attach session token for cross-origin environments where third-party cookies are blocked
  const sessionToken = getSessionToken();
  if (sessionToken) {
    if (!headers['Authorization']) {
      headers['Authorization'] = `Bearer ${sessionToken}`;
    }
    if (!headers['X-Session-Token']) {
      headers['X-Session-Token'] = sessionToken;
    }
  }

  // AbortController timeout handling (default 30s timeout)
  const timeoutMs = options.timeout ?? 30000;
  let timer = null;
  let signal = options.signal;

  if (!signal && timeoutMs > 0 && typeof AbortController !== 'undefined') {
    const controller = new AbortController();
    signal = controller.signal;
    timer = setTimeout(() => controller.abort(), timeoutMs);
  }

  const config = {
    credentials: 'include', // Automatically send HttpOnly cs_session cookies if allowed
    ...options,
    headers,
    signal,
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
      throw new Error('Authentication failed: invalid or missing API key or expired session.');
    }

    if (res.status === 403) {
      throw new Error('Access denied: insufficient forensic investigative permissions.');
    }

    if (res.status === 404) {
      throw new Error(`Resource not found: ${endpoint}`);
    }

    if (res.status === 409) {
      throw new Error('Conflict detected with existing investigative record.');
    }

    // Surface upload rejections
    if (res.status === 413) {
      throw new Error('File exceeds maximum allowed upload size (limit: 500 MB).');
    }

    if (res.status === 415) {
      throw new Error('Unsupported file type. Accepted formats: clean CSV, JSON, or XML.');
    }

    // Surface service readiness / availability
    if (res.status === 503) {
      throw new Error('Service Unavailable: backend database or persistent storage is initializing.');
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(formatErrorDetail(errData.detail, res.status));
    }

    return await res.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw err;
    }
    if (err instanceof TypeError && err.message.toLowerCase().includes('fetch')) {
      throw new Error('Unable to connect to ChainSentinel backend server. Verify the service is online.');
    }
    console.error(`API Error [${endpoint}]:`, err);
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export const api = {
  // System Health & Readiness Probes
  getHealth: (options = {}) => request('/health', options),
  getReadiness: (options = {}) => request('/ready', options),

  // Authentication & Session Handshake
  getSession: async (options = {}) => {
    const res = await request('/auth/session', options);
    if (res && res.token) {
      setSessionToken(res.token);
    }
    if (res && res.api_key && typeof localStorage !== 'undefined' && !localStorage.getItem('chainsentinel_api_key')) {
      setApiKey(res.api_key);
    }
    return res;
  },
  login: async (credentials, options = {}) => {
    const res = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
      ...options,
    });
    if (res && res.token) {
      setSessionToken(res.token);
    }
    return res;
  },
  logout: async (options = {}) => {
    const res = await request('/auth/logout', { method: 'POST', ...options });
    setSessionToken(null);
    return res;
  },

  // Alerts & Triage
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

  // Case Dossier Exports (Printable HTML & Structured CSV)
  exportCaseHtml: async (caseId, options = {}) => {
    const url = `${API_BASE}/trace/cases/${encodeURIComponent(caseId)}/export/html`;
    const headers = { ...options.headers };
    const apiKey = getApiKey();
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(url, {
      credentials: 'include',
      headers,
      signal: options.signal,
    });
    if (!res.ok) throw new Error(`Export HTML failed: HTTP ${res.status}`);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    window.open(objectUrl, '_blank');
  },
  exportCaseCsv: async (caseId, options = {}) => {
    const url = `${API_BASE}/trace/cases/${encodeURIComponent(caseId)}/export/csv`;
    const headers = { ...options.headers };
    const apiKey = getApiKey();
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(url, {
      credentials: 'include',
      headers,
      signal: options.signal,
    });
    if (!res.ok) throw new Error(`Export CSV failed: HTTP ${res.status}`);
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
    const headers = {};
    const apiKey = getApiKey();
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(`${API_BASE}/ingest/detect-schema`, {
      method: 'POST',
      credentials: 'include',
      body: form,
      headers,
      signal: options.signal,
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
    const headers = {};
    const apiKey = getApiKey();
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(`${API_BASE}/ingest/upload${query}`, {
      method: 'POST',
      credentials: 'include',
      body: form,
      headers,
      signal: options.signal,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Upload failed: HTTP ${res.status}`);
    }
    return res.json();
  },
  getIngestProfiles: (options = {}) => request('/ingest/profiles', options),

  // Background Operations
  startJob: (endpoint, body = {}, options = {}) =>
    request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
      ...options,
    }),
  getJobStatus: (jobId, options = {}) =>
    request(`/jobs/${encodeURIComponent(jobId)}`, options),
  cancelJob: (jobId, options = {}) =>
    request(`/jobs/${encodeURIComponent(jobId)}/cancel`, {
      method: 'POST',
      ...options,
    }),
};
