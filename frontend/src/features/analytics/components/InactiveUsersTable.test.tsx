import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import InactiveUsersTable from './InactiveUsersTable'

describe('InactiveUsersTable', () => {
  it('renders inactive users', () => {
    render(
      <InactiveUsersTable
        users={[
          {
            user_id: '22222222-2222-4222-8222-222222222222',
            email: 'quiet@example.com',
            full_name: 'Quiet User',
            is_active: true,
            conversation_count: 0,
            question_count: 0,
            last_active_at: null,
          },
        ]}
      />,
    )

    expect(screen.getByText('Quiet User')).toBeInTheDocument()
    expect(screen.getByText('Active account, no recent activity')).toBeInTheDocument()
  })

  it('renders empty state when all users are active', () => {
    render(<InactiveUsersTable users={[]} />)

    expect(screen.getByText('No inactive users')).toBeInTheDocument()
  })
})
