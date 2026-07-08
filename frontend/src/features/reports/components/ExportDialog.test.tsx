import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ExportDialog from './ExportDialog'

const exportMutateAsync = vi.fn()
const showSuccess = vi.fn()
const showError = vi.fn()

vi.mock('../hooks', () => ({
  useExportReport: () => ({
    mutateAsync: exportMutateAsync,
    isPending: false,
  }),
  useReportFormats: () => ({
    isLoading: false,
    data: {
      items: [
        { id: 'csv', label: 'CSV', media_type: 'text/csv', extension: 'csv' },
        { id: 'pdf', label: 'PDF', media_type: 'application/pdf', extension: 'pdf' },
      ],
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
  useToast: () => ({ showSuccess, showError }),
}))

vi.mock('../services/reportsApi', () => ({
  downloadReportFile: vi.fn(),
}))

describe('ExportDialog', () => {
  it('renders format selector and downloads report', async () => {
    exportMutateAsync.mockResolvedValue({
      blob: new Blob(['report']),
      filename: 'user_analytics_20260601_20260624.pdf',
    })

    render(<ExportDialog open onClose={vi.fn()} defaultModule="user" />)

    expect(screen.getByLabelText('Export format')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Export format'), { target: { value: 'pdf' } })
    fireEvent.click(screen.getByRole('button', { name: 'Download Report' }))

    await waitFor(() => {
      expect(exportMutateAsync).toHaveBeenCalledWith({
        module: 'user',
        format: 'pdf',
        date_range: 'last_7_days',
      })
    })
    expect(showSuccess).toHaveBeenCalled()
  })

  it('shows an error toast when export fails', async () => {
    exportMutateAsync.mockRejectedValue({ message: 'Export failed' })

    render(<ExportDialog open onClose={vi.fn()} defaultModule="user" />)
    fireEvent.click(screen.getByRole('button', { name: 'Download Report' }))

    await waitFor(() => {
      expect(showError).toHaveBeenCalledWith('Export failed')
    })
  })
})
