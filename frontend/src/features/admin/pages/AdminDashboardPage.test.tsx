import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import AdminDashboardPage from '../pages/AdminDashboardPage'

describe('AdminDashboardPage', () => {
  it('renders dashboard shell with placeholder metrics', () => {
    render(<AdminDashboardPage />)

    expect(screen.getByRole('heading', { name: 'Administration Dashboard' })).toBeInTheDocument()
    expect(screen.getByLabelText('Total Users: 128')).toBeInTheDocument()
    expect(screen.getByLabelText('Total Documents: 542')).toBeInTheDocument()
    expect(screen.getByLabelText('Collections: 12')).toBeInTheDocument()
    expect(screen.getByLabelText('Storage Usage: 24.6 GB')).toBeInTheDocument()
  })
})
