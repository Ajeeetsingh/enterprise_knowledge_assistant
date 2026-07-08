import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import UserAnalyticsPage from './UserAnalyticsPage'

vi.mock('../hooks', () => ({
  useUserAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      total_users: 10,
      new_users: 2,
      daily_active_users: 4,
      weekly_active_users: 6,
      monthly_active_users: 8,
      active_user_percentage: 40,
      average_conversations_per_user: 1.5,
      average_questions_per_user: 3.2,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useUserGrowth: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      user_registrations: { event_type: 'user_registrations', points: { '2026-06-27': 1 } },
      active_users: { event_type: 'active_users', points: { '2026-06-27': 1 } },
      login_activity: { event_type: 'auth.login.success', points: { '2026-06-27': 1 } },
      conversation_creation: { event_type: 'conversation_creation', points: {} },
      questions_asked: { event_type: 'chat.question.asked', points: { '2026-06-27': 1 } },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useActivityTrend: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      average_conversations_per_user: 1.5,
      average_questions_per_user: 3.2,
      average_engagement_score: 2.35,
      active_users: { event_type: 'active_users', points: { '2026-06-27': 1 } },
      questions_asked: { event_type: 'chat.question.asked', points: { '2026-06-27': 1 } },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useTopUsers: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: { items: [], total: 0, limit: 10, offset: 0 },
    refetch: vi.fn(),
  }),
  useInactiveUsers: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: { items: [], total: 0, limit: 10, offset: 0 },
    refetch: vi.fn(),
  }),
}))

describe('UserAnalyticsPage', () => {
  it('renders KPI cards and section headings', () => {
    render(<UserAnalyticsPage />)

    expect(screen.getByRole('heading', { name: 'User Analytics' })).toBeInTheDocument()
    expect(screen.getByLabelText('Total Users: 10')).toBeInTheDocument()
    expect(screen.getByText('Top Active Users')).toBeInTheDocument()
    expect(screen.getByText('Inactive Users')).toBeInTheDocument()
  })
})
