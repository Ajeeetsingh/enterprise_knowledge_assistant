import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { type ReactElement, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/features/knowledge-domains/services/knowledgeDomainApi', () => ({
  listKnowledgeDomains: vi.fn(),
  createKnowledgeDomain: vi.fn(),
}))

import * as knowledgeDomainApi from '@/features/knowledge-domains/services/knowledgeDomainApi'

import DocumentUploadDialog from './DocumentUploadDialog'

const DOMAIN = {
  id: 'domain-finance',
  name: 'Finance',
  description: null,
}

function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('DocumentUploadDialog', () => {
  beforeEach(() => {
    vi.mocked(knowledgeDomainApi.listKnowledgeDomains).mockResolvedValue([DOMAIN])
  })

  async function selectDomain(user: ReturnType<typeof userEvent.setup>) {
    const select = await screen.findByLabelText('Knowledge Domain')
    await user.selectOptions(select, DOMAIN.id)
  }

  it('allows selecting multiple files via the file picker', async () => {
    const user = userEvent.setup()
    const onUpload = vi.fn()

    renderWithProviders(
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        onClose={vi.fn()}
        onUpload={onUpload}
      />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input).toHaveAttribute('multiple')

    const files = [
      new File(['alpha'], 'a.pdf', { type: 'application/pdf' }),
      new File(['beta'], 'b.pdf', { type: 'application/pdf' }),
    ]
    await user.upload(input, files)
    await selectDomain(user)

    expect(await screen.findByText('2 files selected')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Upload 2 files' }))
    expect(onUpload).toHaveBeenCalledWith(files, DOMAIN.id)
  })

  it('keeps Upload disabled until a knowledge domain is selected', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        onClose={vi.fn()}
        onUpload={vi.fn()}
      />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, [new File(['a'], 'a.pdf', { type: 'application/pdf' })])

    const uploadButton = await screen.findByRole('button', { name: 'Upload' })
    expect(uploadButton).toBeDisabled()
    await selectDomain(user)
    expect(uploadButton).toBeEnabled()
  })

  it('supports drag-and-drop of multiple files', async () => {
    renderWithProviders(
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        onClose={vi.fn()}
        onUpload={vi.fn()}
      />,
    )

    const dropzone = screen.getByText(/Drop up to 10 files/i).closest('.upload-dropzone')
    fireEvent.drop(dropzone!, {
      dataTransfer: {
        files: [
          new File(['a'], 'drop-a.pdf', { type: 'application/pdf' }),
          new File(['b'], 'drop-b.pdf', { type: 'application/pdf' }),
        ],
      },
    })

    expect(await screen.findByText('drop-a.pdf')).toBeInTheDocument()
    expect(screen.getByText('drop-b.pdf')).toBeInTheDocument()
  })

  it('shows mixed valid and invalid files without discarding invalid ones', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        onClose={vi.fn()}
        onUpload={vi.fn()}
      />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, {
      target: {
        files: [
          new File(['ok'], 'ok.pdf', { type: 'application/pdf' }),
          new File(['bad'], 'bad.exe', { type: 'application/octet-stream' }),
        ],
      },
    })

    expect(await screen.findByText('ok.pdf')).toBeInTheDocument()
    expect(screen.getByText('bad.exe')).toBeInTheDocument()
    expect(screen.getByText(/Unsupported file type/)).toBeInTheDocument()
    await selectDomain(user)
    expect(screen.getByRole('button', { name: 'Upload' })).toBeEnabled()
  })

  it('skips duplicate selections with a clear message', async () => {
    renderWithProviders(
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        onClose={vi.fn()}
        onUpload={vi.fn()}
      />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['a'], 'same.pdf', { type: 'application/pdf' })
    Object.defineProperty(file, 'lastModified', { value: 42 })

    fireEvent.change(input, { target: { files: [file] } })
    await screen.findByText('same.pdf')
    fireEvent.change(input, { target: { files: [file] } })

    expect(await screen.findByText('1 file selected')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('same.pdf is already selected.')
    })
  })

  it('shows Already exists for duplicate upload progress, not Failed', () => {
    const file = new File(['x'], 'mmf-statistics-04-2026.pdf', { type: 'application/pdf' })
    renderWithProviders(
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        summary="No new documents were uploaded. The selected document already exists."
        uploadProgress={[
          {
            id: '1',
            file,
            filename: 'mmf-statistics-04-2026.pdf',
            size: 2048,
            status: 'duplicate',
            error: 'This document has already been uploaded.',
          },
        ]}
        onClose={vi.fn()}
        onUpload={vi.fn()}
        onRetryFailed={vi.fn()}
      />,
    )

    expect(screen.getByText('Already exists')).toBeInTheDocument()
    expect(screen.getByText('This document has already been uploaded.')).toBeInTheDocument()
    expect(screen.queryByText('Failed')).not.toBeInTheDocument()
    expect(screen.queryByText('An unexpected error occurred.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Retry failed' })).not.toBeInTheDocument()
    expect(screen.getByText(/No new documents were uploaded/)).toBeInTheDocument()
  })

  it('removes an individual selected file', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        onClose={vi.fn()}
        onUpload={vi.fn()}
      />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, [
      new File(['a'], 'keep.pdf', { type: 'application/pdf' }),
      new File(['b'], 'remove.pdf', { type: 'application/pdf' }),
    ])

    await user.click(screen.getAllByRole('button', { name: 'Remove' })[1]!)
    expect(screen.queryByText('remove.pdf')).not.toBeInTheDocument()
    expect(screen.getByText('keep.pdf')).toBeInTheDocument()
  })
})
