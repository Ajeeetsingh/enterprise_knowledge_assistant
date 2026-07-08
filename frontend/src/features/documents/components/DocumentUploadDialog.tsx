import { type ChangeEvent, type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import { cn } from '@/utils/cn'

import {
  MAX_DOCUMENT_FILE_SIZE_BYTES,
  SUPPORTED_DOCUMENT_ACCEPT,
  SUPPORTED_DOCUMENT_EXTENSIONS,
} from '../constants'

export interface DocumentUploadDialogProps {
  isOpen: boolean
  isUploading: boolean
  error: string | null
  onClose: () => void
  onUpload: (file: File) => void
}

function validateFile(file: File | null): string | null {
  if (!file) return 'Please select a file to upload.'

  const extension = file.name.includes('.')
    ? `.${file.name.split('.').pop()?.toLowerCase()}`
    : ''

  if (!SUPPORTED_DOCUMENT_EXTENSIONS.includes(extension as (typeof SUPPORTED_DOCUMENT_EXTENSIONS)[number])) {
    return `Unsupported file type. Allowed: ${SUPPORTED_DOCUMENT_EXTENSIONS.join(', ')}`
  }

  if (file.size > MAX_DOCUMENT_FILE_SIZE_BYTES) {
    return 'File exceeds the 50 MB upload limit.'
  }

  return null
}

export default function DocumentUploadDialog({
  isOpen,
  isUploading,
  error,
  onClose,
  onUpload,
}: DocumentUploadDialogProps) {
  const titleId = useId()
  const inputId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) {
      setSelectedFile(null)
      setFieldError(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    fileInputRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isUploading) onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isUploading, onClose])

  if (!isOpen) return null

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setFieldError(validateFile(file))
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const validationError = validateFile(selectedFile)
    if (validationError) {
      setFieldError(validationError)
      return
    }
    if (selectedFile) onUpload(selectedFile)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={() => {
        if (!isUploading) onClose()
      }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cn(
          'w-full max-w-lg rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Upload document
        </h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Supported formats: PDF, DOCX, TXT, CSV, JSON, XLSX (max 50 MB).
        </p>

        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label
              htmlFor={inputId}
              className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-200"
            >
              Choose file
            </label>
            <input
              ref={fileInputRef}
              id={inputId}
              type="file"
              accept={SUPPORTED_DOCUMENT_ACCEPT}
              disabled={isUploading}
              className="block w-full text-sm text-neutral-700 file:mr-3 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-primary-100 disabled:opacity-50 dark:text-neutral-200 dark:file:bg-primary-900/30 dark:file:text-primary-300"
              onChange={handleFileChange}
            />
            {selectedFile && (
              <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                Selected: {selectedFile.name} ({Math.ceil(selectedFile.size / 1024)} KB)
              </p>
            )}
            {fieldError && (
              <p role="alert" className="mt-2 text-sm text-error-500 dark:text-error-400">
                {fieldError}
              </p>
            )}
          </div>

          {isUploading && (
            <div className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300" role="status">
              <Spinner size="sm" label="Uploading document" />
              Uploading and ingesting document…
            </div>
          )}

          {error && (
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" disabled={isUploading} onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isUploading} disabled={isUploading || !selectedFile}>
              Upload
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
