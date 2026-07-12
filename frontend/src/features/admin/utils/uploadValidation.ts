import {
  MAX_BATCH_UPLOAD_FILES,
  MAX_DOCUMENT_FILE_SIZE_BYTES,
  MAX_DOCUMENT_FILE_SIZE_MB,
  SUPPORTED_DOCUMENT_EXTENSIONS,
} from '@/features/documents/constants'

export { MAX_BATCH_UPLOAD_FILES, MAX_DOCUMENT_FILE_SIZE_MB }

function getFileExtension(filename: string): string {
  return filename.includes('.') ? `.${filename.split('.').pop()?.toLowerCase()}` : ''
}

export function validateDocumentFile(file: File | null): string | null {
  if (!file) return 'Please select a file to upload.'

  const extension = getFileExtension(file.name)

  if (
    !SUPPORTED_DOCUMENT_EXTENSIONS.includes(
      extension as (typeof SUPPORTED_DOCUMENT_EXTENSIONS)[number],
    )
  ) {
    return 'Unsupported file type.'
  }

  if (file.size > MAX_DOCUMENT_FILE_SIZE_BYTES) {
    return `File exceeds the ${MAX_DOCUMENT_FILE_SIZE_MB}MB limit.`
  }

  return null
}

export function validateDocumentFileSelection(files: File[]): string | null {
  if (files.length === 0) {
    return 'Please select at least one file to upload.'
  }

  if (files.length > MAX_BATCH_UPLOAD_FILES) {
    return `You can upload up to ${MAX_BATCH_UPLOAD_FILES} files at once. ${files.length} selected.`
  }

  const oversized = files.filter((file) => file.size > MAX_DOCUMENT_FILE_SIZE_BYTES)
  if (oversized.length > 0) {
    return `${oversized.map((file) => file.name).join(', ')} exceed(s) the ${MAX_DOCUMENT_FILE_SIZE_MB}MB limit.`
  }

  const unsupported = files.filter((file) => validateDocumentFile(file) === 'Unsupported file type.')
  if (unsupported.length > 0) {
    return `${unsupported.map((file) => file.name).join(', ')}: unsupported file type.`
  }

  return null
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
