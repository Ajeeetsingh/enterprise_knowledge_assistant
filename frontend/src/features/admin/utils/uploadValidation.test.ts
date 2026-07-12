import { describe, expect, it } from 'vitest'

import { MAX_BATCH_UPLOAD_FILES } from './uploadValidation'
import { validateDocumentFile, validateDocumentFileSelection } from './uploadValidation'

function createFile(name: string, size: number, type = 'application/pdf'): File {
  return new File([new Uint8Array(size)], name, { type })
}

describe('validateDocumentFile', () => {
  it('requires a selected file', () => {
    expect(validateDocumentFile(null)).toBe('Please select a file to upload.')
  })

  it('rejects unsupported file types', () => {
    expect(validateDocumentFile(createFile('notes.exe', 100))).toBe('Unsupported file type.')
  })

  it('rejects files over the size limit', () => {
    expect(validateDocumentFile(createFile('large.pdf', 51 * 1024 * 1024))).toBe(
      'File exceeds the 50MB limit.',
    )
  })

  it('accepts supported files', () => {
    expect(validateDocumentFile(createFile('policy.pdf', 1024))).toBeNull()
  })
})

describe('validateDocumentFileSelection', () => {
  it('requires at least one file', () => {
    expect(validateDocumentFileSelection([])).toBe('Please select at least one file to upload.')
  })

  it('rejects batches over the file cap', () => {
    const files = Array.from({ length: MAX_BATCH_UPLOAD_FILES + 1 }, (_, index) =>
      createFile(`doc-${index}.pdf`, 1024),
    )

    expect(validateDocumentFileSelection(files)).toBe(
      `You can upload up to ${MAX_BATCH_UPLOAD_FILES} files at once. 11 selected.`,
    )
  })

  it('rejects oversized files in a batch', () => {
    const files = [
      createFile('ok.pdf', 1024),
      createFile('big.pdf', 51 * 1024 * 1024),
    ]

    expect(validateDocumentFileSelection(files)).toBe('big.pdf exceed(s) the 50MB limit.')
  })

  it('accepts valid batches', () => {
    const files = [
      createFile('one.pdf', 1024),
      createFile('two.pdf', 2048),
    ]

    expect(validateDocumentFileSelection(files)).toBeNull()
  })
})
