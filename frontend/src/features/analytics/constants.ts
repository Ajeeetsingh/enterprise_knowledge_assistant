export const ANALYTICS_REFRESH_INTERVAL_MS = 60_000

export const DATE_RANGE_PRESET_OPTIONS = [
  { value: 'today', label: 'Today' },
  { value: 'last_7_days', label: 'Last 7 Days' },
  { value: 'last_30_days', label: 'Last 30 Days' },
  { value: 'last_90_days', label: 'Last 90 Days' },
  { value: 'custom', label: 'Custom Range' },
] as const

export const DEFAULT_DATE_RANGE_PRESET = 'last_7_days'
