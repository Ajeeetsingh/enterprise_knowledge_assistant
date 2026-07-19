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

  it('keeps invalid files visible with a per-file error', async () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'bad.exe', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [file] } })

    expect(await screen.findByText('bad.exe')).toBeInTheDocument()
    expect(screen.getByText(/Unsupported file type/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
  })

  it('accepts up to the batch cap and reports overflow', async () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const files = Array.from({ length: MAX_BATCH_UPLOAD_FILES + 1 }, (_, index) =>
      new File([`content-${index}`], `doc-${index}.pdf`, { type: 'application/pdf' }),
    )
    fireEvent.change(input, { target: { files } })

    expect(await screen.findByRole('alert')).toHaveTextContent(/up to 10 files/)
    expect(screen.getByText('10 / 10 files selected')).toBeInTheDocument()
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
      new File(['policy-bytes'], 'policy.pdf', { type: 'application/pdf' }),
      new File(['handbook-bytes'], 'handbook.pdf', { type: 'application/pdf' }),
    ]
    await user.upload(input, files)
    await screen.findByText('handbook.pdf')
    await user.click(screen.getByRole('button', { name: 'Upload 2 files' }))

    expect(onUpload).toHaveBeenCalledWith(files)
  })

  it('adds files to an existing selection and skips duplicates', async () => {
    const user = userEvent.setup()
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const first = new File(['a'], 'one.pdf', { type: 'application/pdf' })
    Object.defineProperty(first, 'lastModified', { value: 100 })
    const second = new File(['b'], 'two.pdf', { type: 'application/pdf' })
    Object.defineProperty(second, 'lastModified', { value: 200 })
    const duplicate = new File(['a'], 'one.pdf', { type: 'application/pdf' })
    Object.defineProperty(duplicate, 'lastModified', { value: 100 })

    await user.upload(input, [first])
    await user.upload(input, [second, duplicate])

    expect(screen.getByText('one.pdf')).toBeInTheDocument()
    expect(screen.getByText('two.pdf')).toBeInTheDocument()
    expect(await screen.findByText('2 / 10 files selected')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'one.pdf is already selected.',
    )
  })

  it('removes a selected file', async () => {
    const user = userEvent.setup()
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, [
      new File(['a'], 'keep.pdf', { type: 'application/pdf' }),
      new File(['b'], 'drop.pdf', { type: 'application/pdf' }),
    ])

    expect(await screen.findByText('keep.pdf')).toBeInTheDocument()
    expect(screen.getByText('drop.pdf')).toBeInTheDocument()

    const removeButtons = await screen.findAllByRole('button', { name: 'Remove' })
    await user.click(removeButtons[1]!)

    expect(screen.queryByText('drop.pdf')).not.toBeInTheDocument()
    expect(screen.getByText('keep.pdf')).toBeInTheDocument()
  })

  it('supports drag-and-drop of multiple files', async () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const dropzone = screen.getByText(/Drop up to 10 files/i).closest('.upload-dropzone')
    expect(dropzone).toBeTruthy()

    const files = [
      new File(['a'], 'dnd-a.pdf', { type: 'application/pdf' }),
      new File(['b'], 'dnd-b.pdf', { type: 'application/pdf' }),
    ]
    fireEvent.drop(dropzone!, {
      dataTransfer: { files },
    })

    expect(await screen.findByText('dnd-a.pdf')).toBeInTheDocument()
    expect(screen.getByText('dnd-b.pdf')).toBeInTheDocument()
  })

  it('renders per-file upload progress rows', () => {
    const file = new File(['x'], 'one.pdf', { type: 'application/pdf' })
    render(
      <DocumentUploadForm
        isUploading
        error={null}
        uploadProgress={[
          {
            id: '1',
            file,
            filename: 'one.pdf',
            size: 1024,
            status: 'completed',
          },
          {
            id: '2',
            file,
            filename: 'two.pdf',
            size: 2048,
            status: 'failed',
            error: 'Timeout',
          },
          {
            id: '3',
            file,
            filename: 'three.pdf',
            size: 512,
            status: 'duplicate',
            error: 'This document has already been uploaded.',
          },
        ]}
        onUpload={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('Upload progress')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(screen.getByText('Timeout')).toBeInTheDocument()
    expect(screen.getByText('Already exists')).toBeInTheDocument()
    expect(screen.getByText('This document has already been uploaded.')).toBeInTheDocument()
    expect(screen.queryByText('Duplicate')).not.toBeInTheDocument()
  })

  it('shows Retry failed only for genuine failures, not duplicates', () => {
    const file = new File(['x'], 'dup.pdf', { type: 'application/pdf' })
    const onRetryFailed = vi.fn()
    render(
      <DocumentUploadForm
        isUploading={false}
        error={null}
        uploadProgress={[
          {
            id: '1',
            file,
            filename: 'dup.pdf',
            size: 1024,
            status: 'duplicate',
            error: 'This document has already been uploaded.',
          },
        ]}
        onUpload={vi.fn()}
        onRetryFailed={onRetryFailed}
      />,
    )

    expect(screen.queryByRole('button', { name: 'Retry failed' })).not.toBeInTheDocument()
  })
})
