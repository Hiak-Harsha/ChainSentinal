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
});
