import { type ChangeEvent, type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import {
  SUPPORTED_DOCUMENT_ACCEPT,
  SUPPORTED_DOCUMENT_EXTENSIONS,
} from '@/features/documents/constants'

import { validateDocumentFile } from '../utils/uploadValidation'

export interface DocumentUploadFormProps {
  isUploading: boolean
  error: string | null
  resetKey?: number
  onUpload: (file: File) => void
}

export default function DocumentUploadForm({
  isUploading,
  error,
  resetKey = 0,
  onUpload,
}: DocumentUploadFormProps) {
  const inputId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)

  useEffect(() => {
    setSelectedFile(null)
    setFieldError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [resetKey])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
    setFieldError(validateDocumentFile(file))
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const validationError = validateDocumentFile(selectedFile)
    if (validationError) {
      setFieldError(validationError)
      return
    }
    if (selectedFile) onUpload(selectedFile)
  }

  return (
    <section
      aria-labelledby="admin-upload-form-heading"
      className="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-700 dark:bg-neutral-900"
    >
      <h3
        id="admin-upload-form-heading"
        className="text-lg font-semibold text-neutral-900 dark:text-neutral-50"
      >
        Upload Document
      </h3>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        Supported formats: {SUPPORTED_DOCUMENT_EXTENSIONS.join(', ')} (max 50 MB).
      </p>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <div>
          <label
            htmlFor={inputId}
            className="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-200"
          >
            Document file
          </label>
          <input
            ref={fileInputRef}
            id={inputId}
            type="file"
            accept={SUPPORTED_DOCUMENT_ACCEPT}
            disabled={isUploading}
            aria-describedby={fieldError ? `${inputId}-error` : undefined}
            className="block w-full text-sm text-neutral-700 file:mr-3 file:rounded-md file:border-0 file:bg-primary-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-primary-100 disabled:opacity-50 dark:text-neutral-200 dark:file:bg-primary-900/30 dark:file:text-primary-300"
            onChange={handleFileChange}
          />
          {selectedFile && (
            <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
              Selected: {selectedFile.name} ({Math.ceil(selectedFile.size / 1024)} KB)
            </p>
          )}
          {fieldError && (
            <p
              id={`${inputId}-error`}
              role="alert"
              className="mt-2 text-sm text-error-500 dark:text-error-400"
            >
              {fieldError}
            </p>
          )}
        </div>

        {isUploading && (
          <div
            className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300"
            role="status"
            aria-live="polite"
          >
            <Spinner size="sm" label="Uploading document" />
            Uploading document to the knowledge base…
          </div>
        )}

        {error && (
          <p role="alert" className="text-sm text-error-500 dark:text-error-400">
            {error}
          </p>
        )}

        <Button type="submit" isLoading={isUploading} disabled={isUploading || !selectedFile}>
          Upload
        </Button>
      </form>
    </section>
  )
}
