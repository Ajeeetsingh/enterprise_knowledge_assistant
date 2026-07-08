import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AdminCollectionsPage from './AdminCollectionsPage'

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
  }),
}))

describe('AdminCollectionsPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders collections page with backend notice', () => {
    render(<AdminCollectionsPage />)

    expect(screen.getByRole('heading', { name: 'Collections Management' })).toBeInTheDocument()
    expect(screen.getByText(/Collections backend not yet implemented/i)).toBeInTheDocument()
    expect(screen.getByText('HR Policies')).toBeInTheDocument()
  })

  it('filters collections by search', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(<AdminCollectionsPage />)

    await user.type(screen.getByLabelText('Search collections'), 'Finance')
    await vi.advanceTimersByTimeAsync(300)

    await waitFor(() => {
      expect(screen.getByText('Finance')).toBeInTheDocument()
      expect(screen.queryByText('HR Policies')).not.toBeInTheDocument()
    })
  })

  it('opens create collection dialog', async () => {
    const user = userEvent.setup()
    render(<AdminCollectionsPage />)

    await user.click(screen.getByRole('button', { name: 'Create collection' }))

    expect(screen.getByRole('dialog', { name: 'Create Collection' })).toBeInTheDocument()
  })
})
