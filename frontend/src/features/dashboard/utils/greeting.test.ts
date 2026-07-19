import { describe, expect, it } from 'vitest'

import {
  buildDashboardGreeting,
  formatRelativeTime,
  getFirstName,
  getTimeOfDayGreeting,
} from './greeting'

describe('dashboard greeting helpers', () => {
  it('extracts the first name from a full name', () => {
    expect(getFirstName('Ada Lovelace')).toBe('Ada')
    expect(getFirstName('  ')).toBeNull()
    expect(getFirstName(undefined)).toBeNull()
  })

  it('builds a time-based greeting when a name is available', () => {
    const morning = new Date('2026-07-17T09:00:00')
    expect(getTimeOfDayGreeting(morning)).toBe('morning')
    expect(buildDashboardGreeting('Ada Lovelace', morning)).toEqual({
      title: 'Good morning, Ada',
      subtitle: 'Your knowledge workspace is ready.',
    })
  })

  it('falls back to Welcome back without a name', () => {
    expect(buildDashboardGreeting(null)).toEqual({
      title: 'Welcome back',
      subtitle: 'Your knowledge workspace is ready.',
    })
  })

  it('formats relative timestamps', () => {
    const now = new Date('2026-07-17T12:00:00Z')
    const label = formatRelativeTime('2026-07-17T11:00:00Z', now)
    expect(label.length).toBeGreaterThan(0)
  })
})
