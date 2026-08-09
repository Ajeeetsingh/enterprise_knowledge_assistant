import {
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react'

import Button from '@/components/ui/Button'
import StatusBadge from '@/components/ui/StatusBadge'
import { KnowledgeDomainField } from '@/features/knowledge-domains'
import { cn } from '@/utils/cn'

import {
  MAX_BATCH_UPLOAD_FILES,
  MAX_DOCUMENT_FILE_SIZE_MB,
  SUPPORTED_DOCUMENT_ACCEPT,
  SUPPORTED_DOCUMENT_EXTENSIONS,
} from '../constants'
import type { BatchUploadItem, BatchUploadItemStatus } from '../hooks/useUploadDocuments'
import {
  countValidSelectedFiles,
  dedupeSelectionByContent,
  formatFileSize,
  mergeUploadSelection,
  type SelectedUploadFile,
} from '../utils/uploadSelection'

export interface DocumentUploadDialogProps {
  isOpen: boolean
  isUploading: boolean
  error: string | null
  uploadProgress?: BatchUploadItem[]
  summary?: string | null
  onClose: () => void
  onUpload: (files: File[], domainId: string) => void
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

export default function DocumentUploadDialog({
  isOpen,
  isUploading,
  error,
  uploadProgress,
  summary,
  onClose,
  onUpload,
  onRetryFailed,
}: DocumentUploadDialogProps) {
  const titleId = useId()
  const inputId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFiles, setSelectedFiles] = useState<SelectedUploadFile[]>([])
  const [selectionNotice, setSelectionNotice] = useState<string | null>(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const [domainId, setDomainId] = useState<string | null>(null)
  const [isCreateDomainOpen, setIsCreateDomainOpen] = useState(false)

  const showingProgress = Boolean(uploadProgress && uploadProgress.length > 0)
  const validCount = countValidSelectedFiles(selectedFiles)
  const invalidCount = selectedFiles.length - validCount
  const failedCount = uploadProgress?.filter((item) => item.status === 'failed').length ?? 0
  const canUpload = validCount > 0 && Boolean(domainId)

  useEffect(() => {
    if (!isOpen) {
      setSelectedFiles([])
      setSelectionNotice(null)
      setIsDragActive(false)
      setDomainId(null)
      setIsCreateDomainOpen(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      // Create Domain modal owns Escape while it is open (capture listener there).
      if (isCreateDomainOpen) return
      if (event.key === 'Escape' && !isUploading) onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isUploading, isCreateDomainOpen, onClose])

  if (!isOpen) return null

  async function applyIncomingFiles(incoming: File[]) {
    if (isUploading || showingProgress) return
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
    if (!isUploading && !showingProgress) setIsDragActive(true)
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
    if (isUploading || showingProgress) return
    setSelectedFiles((current) => current.filter((item) => item.id !== id))
    setSelectionNotice(null)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (isUploading || showingProgress) return
    const validFiles = selectedFiles
      .filter((item) => !item.validationError)
      .map((item) => item.file)
    if (validFiles.length === 0) {
      setSelectionNotice('Please select at least one valid file to upload.')
      return
    }
    if (!domainId) {
      setSelectionNotice('Please select a Knowledge Domain.')
      return
    }
    onUpload(validFiles, domainId)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      data-testid="document-upload-backdrop"
      onPointerDown={(event) => {
        // pointerdown (not click) avoids click-through when Create Domain unmounts
        // under the cursor after a successful create.
        if (event.target !== event.currentTarget) return
        if (isUploading || isCreateDomainOpen) return
        onClose()
      }}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="document-upload-dialog"
        className={cn(
          'w-full max-w-lg rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Upload documents
        </h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
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
                  isUploading && 'upload-dropzone--disabled',
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
                  disabled={isUploading}
                  className="sr-only"
                  onChange={handleFileChange}
                />
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-50">
                  Drop up to {MAX_BATCH_UPLOAD_FILES} files, or{' '}
                  <button
                    type="button"
                    className="text-primary-700 hover:underline dark:text-primary-300"
                    disabled={isUploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    browse
                  </button>
                </p>
                <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                  {selectedFiles.length === 0
                    ? 'No files selected'
                    : `${selectedFiles.length} file${selectedFiles.length === 1 ? '' : 's'} selected`}
                  {invalidCount > 0 ? ` · ${invalidCount} invalid` : ''}
                </p>
              </div>

              {selectionNotice && (
                <p role="alert" className="mt-2 text-sm text-error-500 dark:text-error-400">
                  {selectionNotice}
                </p>
              )}
            </div>
          )}

          {!showingProgress && (
            <KnowledgeDomainField
              value={domainId}
              disabled={isUploading}
              onChange={setDomainId}
              onCreateDialogOpenChange={setIsCreateDomainOpen}
            />
          )}

          {showingProgress ? (
            <ul className="upload-file-list" aria-label="Upload progress">
              {uploadProgress!.map((item) => (
                <li key={item.id} className="upload-file-row">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-50">
                      {item.filename}
                    </p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">
                      {formatFileSize(item.size)}
                    </p>
                    {item.error ? (
                      <p
                        className={cn(
                          'mt-1 text-xs',
                          item.status === 'duplicate'
                            ? 'text-neutral-500 dark:text-neutral-400'
                            : 'text-error-500 dark:text-error-400',
                        )}
                      >
                        {item.error}
                      </p>
                    ) : null}
                  </div>
                  <StatusBadge tone={STATUS_TONES[item.status]}>
                    {STATUS_LABELS[item.status]}
                  </StatusBadge>
                </li>
              ))}
            </ul>
          ) : selectedFiles.length > 0 ? (
            <ul className="upload-file-list" aria-label="Selected files">
              {selectedFiles.map((item) => (
                <li key={item.id} className="upload-file-row">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-50">
                      {item.file.name}
                    </p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">
                      {formatFileSize(item.file.size)}
                    </p>
                    {item.validationError ? (
                      <p className="mt-1 text-xs text-error-500 dark:text-error-400">
                        {item.validationError}
                      </p>
                    ) : (
                      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">Ready</p>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={isUploading}
                    onClick={() => handleRemoveFile(item.id)}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          ) : null}

          {summary && (
            <p className="text-sm text-neutral-600 dark:text-neutral-300" role="status">
              {summary}
            </p>
          )}

          {error && (
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {error}
            </p>
          )}

          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" disabled={isUploading} onClick={onClose}>
              {showingProgress && !isUploading ? 'Close' : 'Cancel'}
            </Button>
            {showingProgress && !isUploading && failedCount > 0 && onRetryFailed ? (
              <Button type="button" variant="secondary" onClick={onRetryFailed}>
                Retry failed
              </Button>
            ) : null}
            {!showingProgress && (
              <Button
                type="submit"
                isLoading={isUploading}
                disabled={isUploading || !canUpload}
              >
                {validCount > 1 ? `Upload ${validCount} files` : 'Upload'}
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
