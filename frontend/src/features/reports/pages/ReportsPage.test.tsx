import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ReportsPage from './ReportsPage'

vi.mock('../hooks', () => ({
  useExportReport: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useReportFormats: () => ({
    isLoading: false,
    data: {
      items: [{ id: 'csv', label: 'CSV', media_type: 'text/csv', extension: 'csv' }],
    },
  }),
  useReportModules: () => ({
    isLoading: false,
    data: {
      items: [{ id: 'user', title: 'User Analytics', description: 'User metrics' }],
    },
  }),
}))

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({ showSuccess: vi.fn(), showError: vi.fn() }),
}))

describe('ReportsPage', () => {
  it('renders reporting controls and export history placeholder', () => {
    render(<ReportsPage />)

    expect(screen.getByText('Reporting & Export')).toBeInTheDocument()
    expect(screen.getByLabelText('Analytics module')).toBeInTheDocument()
    expect(screen.getByLabelText('Export format')).toBeInTheDocument()
    expect(screen.getByText('Export History')).toBeInTheDocument()
  })
})
