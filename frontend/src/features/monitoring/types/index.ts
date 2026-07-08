/**
 * Monitoring types — aligned with backend monitoring API (Phase 9.4B).
 *
 * @see backend/app/schemas/monitoring.py
 */

/** Business metrics summary from GET /monitoring/summary. */
export interface MonitoringSummary {
  total_users: number
  active_users: number
  total_documents: number
  total_conversations: number
  questions_today: number
  failed_logins_today: number
  audit_events_today: number
}

/** Runtime metrics from GET /monitoring/metrics. */
export interface SystemMetrics {
  uptime_seconds: number
  database_connected: boolean
  version: string
}

export function formatUptime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds} second${seconds === 1 ? '' : 's'}`
  }

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    const remainder = seconds % 60
    return remainder > 0 ? `${minutes}m ${remainder}s` : `${minutes} minute${minutes === 1 ? '' : 's'}`
  }

  const hours = Math.floor(minutes / 60)
  const remainderMinutes = minutes % 60
  if (hours < 24) {
    return remainderMinutes > 0
      ? `${hours}h ${remainderMinutes}m`
      : `${hours} hour${hours === 1 ? '' : 's'}`
  }

  const days = Math.floor(hours / 24)
  const remainderHours = hours % 24
  return remainderHours > 0
    ? `${days}d ${remainderHours}h`
    : `${days} day${days === 1 ? '' : 's'}`
}

export function formatMetricValue(value: number): string {
  return value.toLocaleString()
}
