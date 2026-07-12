import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MAX_BATCH_UPLOAD_FILES } from '../utils/uploadValidation'
import DocumentUploadForm from './DocumentUploadForm'

describe('DocumentUploadForm', () => {
  it('renders multi-file upload controls', () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    expect(screen.getByRole('heading', { name: 'Upload Documents' })).toBeInTheDocument()
    expect(screen.getByText(/Drop up to 10 files/i)).toBeInTheDocument()
    expect(screen.getByText('0 / 10 files selected')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
  })

  it('validates unsupported files', async () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'bad.exe', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [file] } })

    expect(screen.getByRole('alert')).toHaveTextContent('bad.exe: unsupported file type.')
  })

  it('rejects more than the batch file cap before upload', () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const files = Array.from({ length: MAX_BATCH_UPLOAD_FILES + 1 }, (_, index) =>
      new File(['content'], `doc-${index}.pdf`, { type: 'application/pdf' }),
    )
    fireEvent.change(input, { target: { files } })

    expect(screen.getByRole('alert')).toHaveTextContent(
      `You can upload up to ${MAX_BATCH_UPLOAD_FILES} files at once. 11 selected.`,
    )
    expect(screen.getByText('0 / 10 files selected')).toBeInTheDocument()
  })

  it('disables upload button during upload', () => {
    render(
      <DocumentUploadForm isUploading error={null} onUpload={vi.fn()} />,
    )

    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
  })

  it('shows upload error state', () => {
    render(
      <DocumentUploadForm
        isUploading={false}
        error="Unable to upload document."
        onUpload={vi.fn()}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to upload document.')
  })

  it('submits valid file batches', async () => {
    const user = userEvent.setup()
    const onUpload = vi.fn()

    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={onUpload} />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const files = [
      new File(['content'], 'policy.pdf', { type: 'application/pdf' }),
      new File(['content'], 'handbook.pdf', { type: 'application/pdf' }),
    ]
    await user.upload(input, files)
    await user.click(screen.getByRole('button', { name: 'Upload 2 files' }))

    expect(onUpload).toHaveBeenCalledWith(files)
    expect(screen.getByText('policy.pdf')).toBeInTheDocument()
    expect(screen.getByText('handbook.pdf')).toBeInTheDocument()
  })

  it('renders per-file upload progress rows', () => {
    render(
      <DocumentUploadForm
        isUploading
        error={null}
        uploadProgress={[
          { id: '1', filename: 'one.pdf', size: 1024, status: 'ready' },
          { id: '2', filename: 'two.pdf', size: 2048, status: 'failed', error: 'Timeout' },
        ]}
        onUpload={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('Upload progress')).toBeInTheDocument()
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('Timeout')).toBeInTheDocument()
  })
})
