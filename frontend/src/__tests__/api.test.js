import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from '../api';

describe('ChainSentinel API Client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('successfully fetches health without throwing', async () => {
    const mockHealth = { status: 'ok', offline: true };
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockHealth,
    });

    const data = await api.getHealth();
    expect(data).toEqual(mockHealth);
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.objectContaining({
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
    }));
  });

  it('surfaces 401 Authentication error with descriptive message', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
    });

    await expect(api.getAlerts()).rejects.toThrow('Authentication failed: invalid or missing API key');
  });

  it('surfaces 429 Rate Limited error with Retry-After header info', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests',
      headers: new Headers({ 'Retry-After': '15' }),
    });

    await expect(api.getAlerts()).rejects.toThrow('Rate limited. Retry in 15s');
  });

  it('surfaces 413 File size error', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 413,
      statusText: 'Payload Too Large',
    });

    await expect(api.getAlerts()).rejects.toThrow('File exceeds maximum allowed upload size');
  });

  it('surfaces 415 Unsupported Media Type error', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 415,
      statusText: 'Unsupported Media Type',
    });

    await expect(api.getAlerts()).rejects.toThrow('Unsupported file type');
  });

  it('parses error detail from JSON response on 400/500 errors', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Custom validation failure' }),
    });

    await expect(api.getAlerts()).rejects.toThrow('Custom validation failure');
  });

  it('constructs query parameters correctly in getAlerts', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [],
    });

    await api.getAlerts({ status: 'ACTIVE', min_risk: 0.7, limit: 25 });
    expect(fetch).toHaveBeenCalledWith(
      '/api/alerts?min_risk=0.7&status=ACTIVE&limit=25',
      expect.anything()
    );
  });

  it('calls getSimilarEntities with encoded entity ID and top_k parameter', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [{ entity_id: 'ENT_target', similarity_score: 0.95 }],
    });

    const res = await api.getSimilarEntities('ENT_abc/123', 8);
    expect(res).toEqual([{ entity_id: 'ENT_target', similarity_score: 0.95 }]);
    expect(fetch).toHaveBeenCalledWith(
      '/api/graph/entities/ENT_abc%2F123/similar?top_k=8',
      expect.anything()
    );
  });

  it('submits alert feedback payload via POST in submitAlertFeedback', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ status: 'feedback_recorded', verdict: 'confirmed_malicious' }),
    });

    const res = await api.submitAlertFeedback('ALT_99', 'confirmed_malicious', 'Operator confirmed');
    expect(res.status).toBe('feedback_recorded');
    expect(fetch).toHaveBeenCalledWith(
      '/api/alerts/ALT_99/feedback',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ verdict: 'confirmed_malicious', notes: 'Operator confirmed' }),
      })
    );
  });

  it('fetches alert timeseries with specified bucket interval', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => [{ bucket: '2026-09-24T00:00:00Z', count: 4, mean_risk: 0.82 }],
    });

    const res = await api.getAlertTimeseries('day');
    expect(res).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      '/api/alerts/timeseries?bucket=day',
      expect.anything()
    );
  });

  it('manages background jobs with startJob and getJobStatus', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: async () => ({ job_id: 'job_456', status: 'pending' }),
    });

    const startRes = await api.startJob('/graph/cluster', { async_mode: true });
    expect(startRes.job_id).toBe('job_456');
    expect(fetch).toHaveBeenCalledWith(
      '/api/graph/cluster',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ async_mode: true }),
      })
    );

    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ job_id: 'job_456', status: 'completed', result: { clusters: 12 } }),
    });

    const statusRes = await api.getJobStatus('job_456');
    expect(statusRes.status).toBe('completed');
    expect(fetch).toHaveBeenCalledWith(
      '/api/jobs/job_456',
      expect.anything()
    );
  });
});
