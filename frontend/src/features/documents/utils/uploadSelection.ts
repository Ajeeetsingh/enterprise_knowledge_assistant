import {
  MAX_BATCH_UPLOAD_FILES,
  MAX_DOCUMENT_FILE_SIZE_BYTES,
  MAX_DOCUMENT_FILE_SIZE_MB,
  SUPPORTED_DOCUMENT_EXTENSIONS,
} from '../constants'
import { sha256Hex } from './fileChecksum'

export { MAX_BATCH_UPLOAD_FILES, MAX_DOCUMENT_FILE_SIZE_MB }

export interface SelectedUploadFile {
  id: string
  file: File
  validationError: string | null
  /** Content hash when computed for batch de-duplication. */
  contentHash?: string
}

function getFileExtension(filename: string): string {
  return filename.includes('.') ? `.${filename.split('.').pop()?.toLowerCase()}` : ''
}

/** Stable identity for duplicate detection within a selection (picker identity). */
export function fileIdentityKey(file: File): string {
  return `${file.name}::${file.size}::${file.lastModified}`
}

export function validateDocumentFile(file: File | null): string | null {
  if (!file) return 'Please select a file to upload.'

  const extension = getFileExtension(file.name)

  if (
    !SUPPORTED_DOCUMENT_EXTENSIONS.includes(
      extension as (typeof SUPPORTED_DOCUMENT_EXTENSIONS)[number],
    )
  ) {
    return `Unsupported file type. Allowed: ${SUPPORTED_DOCUMENT_EXTENSIONS.join(', ')}`
  }

  if (file.size > MAX_DOCUMENT_FILE_SIZE_BYTES) {
    return `File exceeds the ${MAX_DOCUMENT_FILE_SIZE_MB} MB upload limit.`
  }

  return null
}

export function toSelectedUploadFile(file: File): SelectedUploadFile {
  return {
    id: fileIdentityKey(file),
    file,
    validationError: validateDocumentFile(file),
  }
}

export interface MergeUploadSelectionResult {
  files: SelectedUploadFile[]
  /** Non-fatal notices (duplicates skipped, batch cap truncations). */
  notices: string[]
  /** Hard selection error (e.g. empty result after only duplicates). */
  error: string | null
}

function formatDuplicateSelectionNotice(filenames: string[]): string {
  if (filenames.length === 1) {
    return `${filenames[0]} is already selected.`
  }
  if (filenames.length <= 3) {
    return `${filenames.join(', ')} are already selected.`
  }
  return `${filenames.length} files are already selected.`
}

/**
 * Merge newly chosen files into an existing selection.
 * Skips picker-identity duplicates, keeps invalid files visible with per-file errors,
 * and never exceeds {@link MAX_BATCH_UPLOAD_FILES}.
 */
export function mergeUploadSelection(
  existing: SelectedUploadFile[],
  incoming: File[],
  maxFiles: number = MAX_BATCH_UPLOAD_FILES,
): MergeUploadSelectionResult {
  const byId = new Map(existing.map((item) => [item.id, item]))
  const notices: string[] = []
  const duplicateNames: string[] = []
  let skippedForCap = 0

  for (const file of incoming) {
    const id = fileIdentityKey(file)
    if (byId.has(id)) {
      duplicateNames.push(file.name)
      continue
    }
    if (byId.size >= maxFiles) {
      skippedForCap += 1
      continue
    }
    byId.set(id, toSelectedUploadFile(file))
  }

  if (duplicateNames.length > 0) {
    notices.push(formatDuplicateSelectionNotice(duplicateNames))
  }
  if (skippedForCap > 0) {
    notices.push(
      `You can upload up to ${maxFiles} files at once. ${skippedForCap} file${
        skippedForCap === 1 ? ' was' : 's were'
      } not added.`,
    )
  }

  const files = [...byId.values()]
  if (files.length === 0 && incoming.length > 0) {
    return {
      files,
      notices,
      error: notices[0] ?? 'Please select at least one file to upload.',
    }
  }

  return { files, notices, error: null }
}

/**
 * Remove later files that share SHA-256 content with an earlier selection entry.
 * Keeps the first occurrence; surfaces clear "already selected" notices.
 */
export async function dedupeSelectionByContent(
  files: SelectedUploadFile[],
): Promise<MergeUploadSelectionResult> {
  const kept: SelectedUploadFile[] = []
  const seenHashes = new Map<string, string>()
  const duplicateNames: string[] = []

  for (const item of files) {
    if (item.validationError) {
      kept.push(item)
      continue
    }

    const hash = item.contentHash ?? (await sha256Hex(item.file))
    const existingName = seenHashes.get(hash)
    if (existingName) {
      duplicateNames.push(item.file.name)
      continue
    }
    seenHashes.set(hash, item.file.name)
    kept.push({ ...item, contentHash: hash })
  }

  const notices =
    duplicateNames.length > 0 ? [formatDuplicateSelectionNotice(duplicateNames)] : []

  return {
    files: kept,
    notices,
    error: kept.length === 0 && files.length > 0 ? (notices[0] ?? null) : null,
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function countValidSelectedFiles(files: SelectedUploadFile[]): number {
  return files.filter((item) => !item.validationError).length
}

/** Legacy batch validator used by older call sites / tests. */
export function validateDocumentFileSelection(files: File[]): string | null {
  if (files.length === 0) {
    return 'Please select at least one file to upload.'
  }

  if (files.length > MAX_BATCH_UPLOAD_FILES) {
    return `You can upload up to ${MAX_BATCH_UPLOAD_FILES} files at once. ${files.length} selected.`
  }

  for (const file of files) {
    const error = validateDocumentFile(file)
    if (error) {
      return `${file.name}: ${error}`
    }
  }

  return null
}
