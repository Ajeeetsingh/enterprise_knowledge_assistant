import { type ChangeEvent, type DragEvent, type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import StatusBadge from '@/components/ui/StatusBadge'
import { SUPPORTED_DOCUMENT_ACCEPT, SUPPORTED_DOCUMENT_EXTENSIONS } from '@/features/documents/constants'
import type { BatchUploadItem, BatchUploadItemStatus } from '@/features/documents/hooks/useUploadDocuments'
import {
  countValidSelectedFiles,
  dedupeSelectionByContent,
  formatFileSize,
  mergeUploadSelection,
  type SelectedUploadFile,
} from '@/features/documents/utils/uploadSelection'
import { cn } from '@/utils/cn'

import { MAX_BATCH_UPLOAD_FILES, MAX_DOCUMENT_FILE_SIZE_MB } from '../utils/uploadValidation'

export interface DocumentUploadFormProps {
  isUploading: boolean
  error: string | null
  resetKey?: number
  uploadProgress?: BatchUploadItem[]
  summary?: string | null
  onUpload: (files: File[]) => void
  onRetryFailed?: () => void
}

const STATUS_LABELS: Record<BatchUploadItemStatus, string> = {
  queued: 'Queued',
  uploading: 'Uploading',
  processing: 'Processing',
  completed: 'Completed',
  duplicate: 'Already exists',
  failed: 'Failed',
}

const STATUS_TONES: Record<BatchUploadItemStatus, 'neutral' | 'good' | 'warn' | 'bad'> = {
  queued: 'neutral',
  uploading: 'warn',
  processing: 'warn',
  completed: 'good',
  duplicate: 'warn',
  failed: 'bad',
}

export default function DocumentUploadForm({
  isUploading,
  error,
  resetKey = 0,
  uploadProgress,
  summary,
  onUpload,
  onRetryFailed,
}: DocumentUploadFormProps) {
  const inputId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFiles, setSelectedFiles] = useState<SelectedUploadFile[]>([])
  const [selectionNotice, setSelectionNotice] = useState<string | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)

  const isBusy = isUploading
  const showingProgress = Boolean(uploadProgress && uploadProgress.length > 0)
  const validCount = countValidSelectedFiles(selectedFiles)
  const failedCount = uploadProgress?.filter((item) => item.status === 'failed').length ?? 0

  useEffect(() => {
    setSelectedFiles([])
    setSelectionNotice(null)
    setIsDragActive(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [resetKey])

  async function applyIncomingFiles(incoming: File[]) {
    if (isBusy || showingProgress) return
    const merged = mergeUploadSelection(selectedFiles, incoming)
    try {
      const deduped = await dedupeSelectionByContent(merged.files)
      const notices = [...merged.notices, ...deduped.notices]
      setSelectedFiles(deduped.files)
      setSelectionNotice(
        deduped.error ?? merged.error ?? (notices.length > 0 ? notices.join(' ') : null),
      )
    } catch {
      setSelectedFiles(merged.files)
      setSelectionNotice(
        merged.error ?? (merged.notices.length > 0 ? merged.notices.join(' ') : null),
      )
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    void applyIncomingFiles(Array.from(event.target.files ?? []))
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    if (!isBusy && !showingProgress) setIsDragActive(true)
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragActive(false)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragActive(false)
    void applyIncomingFiles(Array.from(event.dataTransfer.files ?? []))
  }

  function handleRemoveFile(id: string) {
    if (isBusy || showingProgress) return
    setSelectedFiles((current) => current.filter((item) => item.id !== id))
    setSelectionNotice(null)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (isBusy || showingProgress) return
    const validFiles = selectedFiles
      .filter((item) => !item.validationError)
      .map((item) => item.file)
    if (validFiles.length === 0) {
      setSelectionNotice('Please select at least one valid file to upload.')
      return
    }
    onUpload(validFiles)
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
        {!showingProgress && (
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
                {selectedFiles.length - validCount > 0
                  ? ` · ${selectedFiles.length - validCount} invalid`
                  : ''}
              </p>
            </div>

            {selectionNotice && (
              <p role="alert" className="mt-2 text-sm text-status-bad">
                {selectionNotice}
              </p>
            )}
          </div>
        )}

        {showingProgress ? (
          <ul className="upload-file-list" aria-label="Upload progress">
            {uploadProgress!.map((item) => (
              <li key={item.id} className="upload-file-row">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{item.filename}</p>
                  <p className="text-xs text-muted">{formatFileSize(item.size)}</p>
                  {item.error ? (
                    <p
                      className={cn(
                        'mt-1 text-xs',
                        item.status === 'duplicate' ? 'text-muted' : 'text-status-bad',
                      )}
                    >
                      {item.error}
                    </p>
                  ) : null}
                </div>
                <StatusBadge tone={STATUS_TONES[item.status]}>{STATUS_LABELS[item.status]}</StatusBadge>
              </li>
            ))}
          </ul>
        ) : selectedFiles.length > 0 ? (
          <ul className="upload-file-list" aria-label="Selected files">
            {selectedFiles.map((item) => (
              <li key={item.id} className="upload-file-row">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{item.file.name}</p>
                  <p className="text-xs text-muted">{formatFileSize(item.file.size)}</p>
                  {item.validationError ? (
                    <p className="mt-1 text-xs text-status-bad">{item.validationError}</p>
                  ) : (
                    <p className="mt-1 text-xs text-muted">Ready</p>
                  )}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isBusy}
                  onClick={() => handleRemoveFile(item.id)}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        ) : null}

        {summary && (
          <p className="text-sm text-muted" role="status">
            {summary}
          </p>
        )}

        {error && (
          <p role="alert" className="text-sm text-status-bad">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {showingProgress && !isUploading && failedCount > 0 && onRetryFailed ? (
            <Button type="button" variant="secondary" onClick={onRetryFailed}>
              Retry failed
            </Button>
          ) : null}
          {!showingProgress && (
            <Button
              type="submit"
              isLoading={isUploading}
              disabled={isUploading || validCount === 0}
            >
              {validCount > 1 ? `Upload ${validCount} files` : 'Upload'}
            </Button>
          )}
        </div>
      </form>
    </section>
  )
}
