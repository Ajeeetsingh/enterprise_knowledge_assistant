import { type ChangeEvent, type DragEvent, type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import StatusBadge from '@/components/ui/StatusBadge'
import { SUPPORTED_DOCUMENT_ACCEPT, SUPPORTED_DOCUMENT_EXTENSIONS } from '@/features/documents/constants'
import { cn } from '@/utils/cn'

import {
  formatFileSize,
  MAX_BATCH_UPLOAD_FILES,
  MAX_DOCUMENT_FILE_SIZE_MB,
  validateDocumentFileSelection,
} from '../utils/uploadValidation'

export type BatchUploadFileStatus = 'queued' | 'uploading' | 'processing' | 'ready' | 'failed'

export interface BatchUploadProgressItem {
  id: string
  filename: string
  size: number
  status: BatchUploadFileStatus
  error?: string
}

export interface DocumentUploadFormProps {
  isUploading: boolean
  error: string | null
  resetKey?: number
  uploadProgress?: BatchUploadProgressItem[]
  onUpload: (files: File[]) => void
}

const STATUS_LABELS: Record<BatchUploadFileStatus, string> = {
  queued: 'Queued',
  uploading: 'Uploading',
  processing: 'Processing',
  ready: 'Ready',
  failed: 'Failed',
}

const STATUS_TONES: Record<BatchUploadFileStatus, 'neutral' | 'good' | 'warn' | 'bad'> = {
  queued: 'neutral',
  uploading: 'warn',
  processing: 'warn',
  ready: 'good',
  failed: 'bad',
}

function statusTone(status: BatchUploadFileStatus) {
  return STATUS_TONES[status]
}

export default function DocumentUploadForm({
  isUploading,
  error,
  resetKey = 0,
  uploadProgress,
  onUpload,
}: DocumentUploadFormProps) {
  const inputId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)

  const isBusy = isUploading
  const showingProgress = Boolean(uploadProgress && uploadProgress.length > 0)

  useEffect(() => {
    setSelectedFiles([])
    setFieldError(null)
    setIsDragActive(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [resetKey])

  function applyFileSelection(files: File[]) {
    const validationError = validateDocumentFileSelection(files)
    setSelectedFiles(validationError ? [] : files)
    setFieldError(validationError)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    applyFileSelection(files)
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    if (!isBusy) setIsDragActive(true)
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragActive(false)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragActive(false)
    if (isBusy) return
    applyFileSelection(Array.from(event.dataTransfer.files ?? []))
  }

  function handleRemoveFile(index: number) {
    if (isBusy) return
    const nextFiles = selectedFiles.filter((_, fileIndex) => fileIndex !== index)
    setFieldError(validateDocumentFileSelection(nextFiles))
    setSelectedFiles(nextFiles)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const validationError = validateDocumentFileSelection(selectedFiles)
    if (validationError) {
      setFieldError(validationError)
      return
    }
    onUpload(selectedFiles)
  }

  return (
    <section
      aria-labelledby="admin-upload-form-heading"
      className="rounded-lg border border-border-subtle bg-surface-raised p-6 shadow-elevation-sm"
    >
      <h3 id="admin-upload-form-heading" className="text-lg font-semibold text-foreground">
        Upload Documents
      </h3>
      <p className="mt-1 text-sm text-muted">
        Supported formats: {SUPPORTED_DOCUMENT_EXTENSIONS.join(', ')}. Up to{' '}
        {MAX_BATCH_UPLOAD_FILES} files per batch, {MAX_DOCUMENT_FILE_SIZE_MB} MB each.
      </p>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <div>
          <div
            className={cn(
              'upload-dropzone',
              isDragActive && 'upload-dropzone--active',
              isBusy && 'upload-dropzone--disabled',
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              id={inputId}
              type="file"
              multiple
              accept={SUPPORTED_DOCUMENT_ACCEPT}
              disabled={isBusy}
              className="sr-only"
              onChange={handleFileChange}
            />
            <p className="text-sm font-medium text-foreground">
              Drop up to {MAX_BATCH_UPLOAD_FILES} files, or{' '}
              <button
                type="button"
                className="text-accent hover:underline"
                disabled={isBusy}
                onClick={() => fileInputRef.current?.click()}
              >
                browse
              </button>
            </p>
            <p className="mt-1 text-xs text-muted">
              {selectedFiles.length} / {MAX_BATCH_UPLOAD_FILES} files selected
            </p>
          </div>

          {fieldError && (
            <p role="alert" className="mt-2 text-sm text-status-bad">
              {fieldError}
            </p>
          )}
        </div>

        {showingProgress ? (
          <ul className="upload-file-list" aria-label="Upload progress">
            {uploadProgress!.map((item) => (
              <li key={item.id} className="upload-file-row">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{item.filename}</p>
                  <p className="text-xs text-muted">{formatFileSize(item.size)}</p>
                  {item.error ? (
                    <p className="mt-1 text-xs text-status-bad">{item.error}</p>
                  ) : null}
                </div>
                <StatusBadge tone={statusTone(item.status)}>{STATUS_LABELS[item.status]}</StatusBadge>
              </li>
            ))}
          </ul>
        ) : selectedFiles.length > 0 ? (
          <ul className="upload-file-list" aria-label="Selected files">
            {selectedFiles.map((file, index) => (
              <li key={`${file.name}-${file.lastModified}`} className="upload-file-row">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{file.name}</p>
                  <p className="text-xs text-muted">{formatFileSize(file.size)}</p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isBusy}
                  onClick={() => handleRemoveFile(index)}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        ) : null}

        {error && (
          <p role="alert" className="text-sm text-status-bad">
            {error}
          </p>
        )}

        <Button
          type="submit"
          isLoading={isUploading}
          disabled={isUploading || selectedFiles.length === 0}
        >
          {selectedFiles.length > 1
            ? `Upload ${selectedFiles.length} files`
            : 'Upload'}
        </Button>
      </form>
    </section>
  )
}
