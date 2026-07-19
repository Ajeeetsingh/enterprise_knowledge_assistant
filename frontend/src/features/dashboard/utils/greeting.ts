/** Greeting helpers for the authenticated dashboard. */

export function getTimeOfDayGreeting(date = new Date()): 'morning' | 'afternoon' | 'evening' {
  const hour = date.getHours()
  if (hour < 12) return 'morning'
  if (hour < 17) return 'afternoon'
  return 'evening'
}

export function getFirstName(fullName: string | null | undefined): string | null {
  if (!fullName) return null
  const first = fullName.trim().split(/\s+/).filter(Boolean)[0]
  return first || null
}

export function buildDashboardGreeting(
  fullName: string | null | undefined,
  date = new Date(),
): { title: string; subtitle: string } {
  const firstName = getFirstName(fullName)
  if (!firstName) {
    return {
      title: 'Welcome back',
      subtitle: 'Your knowledge workspace is ready.',
    }
  }

  const period = getTimeOfDayGreeting(date)
  return {
    title: `Good ${period}, ${firstName}`,
    subtitle: 'Your knowledge workspace is ready.',
  }
}

/** Compact relative time for conversation / document lists. */
export function formatRelativeTime(iso: string, now = new Date()): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''

  const diffMs = date.getTime() - now.getTime()
  const diffSec = Math.round(diffMs / 1000)
  const absSec = Math.abs(diffSec)
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

  if (absSec < 60) return rtf.format(diffSec, 'second')
  const diffMin = Math.round(diffSec / 60)
  if (Math.abs(diffMin) < 60) return rtf.format(diffMin, 'minute')
  const diffHour = Math.round(diffMin / 60)
  if (Math.abs(diffHour) < 24) return rtf.format(diffHour, 'hour')
  const diffDay = Math.round(diffHour / 24)
  if (Math.abs(diffDay) < 30) return rtf.format(diffDay, 'day')
  const diffMonth = Math.round(diffDay / 30)
  if (Math.abs(diffMonth) < 12) return rtf.format(diffMonth, 'month')
  return rtf.format(Math.round(diffMonth / 12), 'year')
}
