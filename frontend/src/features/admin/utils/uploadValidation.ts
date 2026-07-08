import {
  MAX_DOCUMENT_FILE_SIZE_BYTES,
  SUPPORTED_DOCUMENT_EXTENSIONS,
} from '@/features/documents/constants'

export function validateDocumentFile(file: File | null): string | null {
  if (!file) return 'Please select a file to upload.'

  const extension = file.name.includes('.')
    ? `.${file.name.split('.').pop()?.toLowerCase()}`
    : ''

  if (
    !SUPPORTED_DOCUMENT_EXTENSIONS.includes(
      extension as (typeof SUPPORTED_DOCUMENT_EXTENSIONS)[number],
    )
  ) {
    return 'Unsupported file type.'
  }

  if (file.size > MAX_DOCUMENT_FILE_SIZE_BYTES) {
    return 'File exceeds size limit.'
  }

  return null
}
