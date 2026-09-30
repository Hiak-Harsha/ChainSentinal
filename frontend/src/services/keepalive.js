/**
 * ChainSentinel Render Backend Keep-Alive Trigger Service
 *
 * Keeps Render free-tier instances active and prevents them from spinning down
 * after the default 15 minutes of inactivity.
 *
 * Capabilities:
 * 1. Background heartbeat timer (defaults to every 12-14 minutes, safely under Render's 15-min limit)
 * 2. Instant wake-up on tab visibility / focus if idle > 8 minutes
 * 3. Graceful handling of cold starts (60s timeout allowance)
 * 4. Observable connection status for the UI shell
 */

import { api, API_BASE } from '../api';

let keepAliveInterval = null;
let lastPingTimestamp = Date.now();
let currentStatus = 'unknown'; // 'awake' | 'waking' | 'offline' | 'unknown'
const statusListeners = new Set();

function notifyStatus(status, details = null) {
  currentStatus = status;
  for (const listener of statusListeners) {
    try {
      listener(status, details);
    } catch (e) {
      console.error('[KeepAlive] Listener error:', e);
    }
  }
}

/**
 * Execute a keep-alive ping against the backend /api/health endpoint.
 * Accepts a generous timeout (default 60s) to allow Render free tier containers
 * time to spin up if they are currently cold-starting.
 */
export async function pingBackend(timeoutMs = 60000) {
  lastPingTimestamp = Date.now();
  notifyStatus('waking');

  try {
    const health = await api.getHealth({ timeout: timeoutMs });
    if (health && health.status === 'ok') {
      notifyStatus('awake', health);
      return { success: true, health };
    }
    notifyStatus('offline', health);
    return { success: false, health };
  } catch (err) {
    notifyStatus('offline', err);
    return { success: false, error: err.message };
  }
}

/**
 * Subscribe to keep-alive status changes.
 * @param {(status: 'awake'|'waking'|'offline', details: any) => void} callback
 * @returns {() => void} unsubscribe function
 */
export function subscribeKeepAliveStatus(callback) {
  statusListeners.add(callback);
  callback(currentStatus, null);
  return () => {
    statusListeners.delete(callback);
  };
}

/**
 * Start the keep-alive background timer and event listeners.
 * @param {number} intervalMinutes - Interval between pings in minutes (default 12)
 * @returns {() => void} cleanup function
 */
export function startKeepAlive(intervalMinutes = 12) {
  if (keepAliveInterval) {
    clearInterval(keepAliveInterval);
  }

  const intervalMs = Math.max(1, intervalMinutes) * 60 * 1000;

  // Background interval timer
  keepAliveInterval = setInterval(() => {
    pingBackend();
  }, intervalMs);

  // Tab visibility wake-up: if user switches back to this tab and >8 min elapsed, ping immediately
  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      const elapsedMinutes = (Date.now() - lastPingTimestamp) / (60 * 1000);
      if (elapsedMinutes >= 8) {
        pingBackend();
      }
    }
  };

  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', handleVisibilityChange);
  }

  return () => {
    if (keepAliveInterval) {
      clearInterval(keepAliveInterval);
      keepAliveInterval = null;
    }
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    }
  };
}

/**
 * Get current keep-alive telemetry state.
 */
export function getKeepAliveState() {
  return {
    status: currentStatus,
    lastPing: new Date(lastPingTimestamp).toISOString(),
    apiBase: API_BASE,
  };
}
