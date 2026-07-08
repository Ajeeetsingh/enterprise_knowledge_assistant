import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import TopUsersTable from './TopUsersTable'

describe('TopUsersTable', () => {
  it('renders user rows', () => {
    render(
      <TopUsersTable
        users={[
          {
            user_id: '11111111-1111-4111-8111-111111111111',
            email: 'active@example.com',
            full_name: 'Active User',
            is_active: true,
            conversation_count: 2,
            question_count: 5,
            last_active_at: '2026-06-27T10:00:00Z',
          },
        ]}
      />,
    )

    expect(screen.getByText('Active User')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders empty state when no users are provided', () => {
    render(<TopUsersTable users={[]} />)

    expect(screen.getByText('No active users')).toBeInTheDocument()
  })
})
