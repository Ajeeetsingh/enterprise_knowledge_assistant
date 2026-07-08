import { describe, expect, it } from 'vitest'

import { validateDocumentFile } from './uploadValidation'

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
      'File exceeds size limit.',
    )
  })

  it('accepts supported files', () => {
    expect(validateDocumentFile(createFile('policy.pdf', 1024))).toBeNull()
  })
})
