import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { pingBackend, startKeepAlive, subscribeKeepAliveStatus } from '../services/keepalive';
import { api } from '../api';

describe('ChainSentinel Keep-Alive Trigger Service', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'debug').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('pingBackend calls api.getHealth with extended timeout', async () => {
    const mockHealth = { status: 'ok', version: '0.1.0' };
    const getHealthSpy = vi.spyOn(api, 'getHealth').mockResolvedValueOnce(mockHealth);

    const result = await pingBackend(60000);
    expect(result.success).toBe(true);
    expect(result.health).toEqual(mockHealth);
    expect(getHealthSpy).toHaveBeenCalledWith({ timeout: 60000 });
  });

  it('pingBackend handles errors gracefully when backend is offline/spinning up', async () => {
    vi.spyOn(api, 'getHealth').mockRejectedValueOnce(new Error('Network error or cold-starting'));

    const result = await pingBackend(60000);
    expect(result.success).toBe(false);
    expect(result.error).toContain('cold-starting');
  });

  it('startKeepAlive sets up periodic timer and cleans up on unmount', async () => {
    const getHealthSpy = vi.spyOn(api, 'getHealth').mockResolvedValue({ status: 'ok' });

    const stop = startKeepAlive(12);

    // Fast-forward 12 minutes
    await vi.advanceTimersByTimeAsync(12 * 60 * 1000);
    expect(getHealthSpy).toHaveBeenCalledTimes(1);

    // Fast-forward another 12 minutes
    await vi.advanceTimersByTimeAsync(12 * 60 * 1000);
    expect(getHealthSpy).toHaveBeenCalledTimes(2);

    stop();

    // Advance more time; no more calls should happen
    await vi.advanceTimersByTimeAsync(12 * 60 * 1000);
    expect(getHealthSpy).toHaveBeenCalledTimes(2);
  });

  it('subscribeKeepAliveStatus notifies listeners of awake status', async () => {
    vi.spyOn(api, 'getHealth').mockResolvedValueOnce({ status: 'ok' });

    const statuses = [];
    const unsubscribe = subscribeKeepAliveStatus((status) => {
      statuses.push(status);
    });

    await pingBackend();

    expect(statuses).toContain('waking');
    expect(statuses).toContain('awake');

    unsubscribe();
  });
});
