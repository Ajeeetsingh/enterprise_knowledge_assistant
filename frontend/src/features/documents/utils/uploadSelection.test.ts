import { describe, expect, it } from 'vitest'

import { MAX_BATCH_UPLOAD_FILES } from '../constants'
import {
  dedupeSelectionByContent,
  fileIdentityKey,
  mergeUploadSelection,
  toSelectedUploadFile,
  validateDocumentFile,
} from './uploadSelection'

function createFile(name: string, size = 100, lastModified = 1, content = 'x'): File {
  const file = new File([content.padEnd(size, 'x')], name, { type: 'application/pdf' })
  Object.defineProperty(file, 'lastModified', { value: lastModified })
  return file
}

describe('uploadSelection', () => {
  it('builds a stable identity key', () => {
    const file = createFile('a.pdf', 10, 99)
    expect(fileIdentityKey(file)).toBe('a.pdf::10::99')
  })

  it('marks unsupported files invalid without discarding them', () => {
    const selected = toSelectedUploadFile(new File(['x'], 'bad.exe'))
    expect(selected.validationError).toMatch(/Unsupported file type/)
  })

  it('skips the same file selected twice with a clear message', () => {
    const first = createFile('one.pdf', 10, 1)
    const existing = [toSelectedUploadFile(first)]
    const duplicate = createFile('one.pdf', 10, 1)

    const result = mergeUploadSelection(existing, [duplicate])

    expect(result.files).toHaveLength(1)
    expect(result.notices[0]).toBe('one.pdf is already selected.')
  })

  it('summarises multiple selection duplicates', () => {
    const a = createFile('a.pdf', 10, 1)
    const b = createFile('b.pdf', 10, 2)
    const existing = [toSelectedUploadFile(a), toSelectedUploadFile(b)]
    const result = mergeUploadSelection(existing, [
      createFile('a.pdf', 10, 1),
      createFile('b.pdf', 10, 2),
    ])

    expect(result.notices[0]).toBe('a.pdf, b.pdf are already selected.')
  })

  it('detects same content under a different filename in the selection', async () => {
    const first = toSelectedUploadFile(createFile('report.pdf', 12, 1, 'same-bytes'))
    const renamed = toSelectedUploadFile(createFile('report-copy.pdf', 12, 2, 'same-bytes'))

    const result = await dedupeSelectionByContent([first, renamed])

    expect(result.files).toHaveLength(1)
    expect(result.files[0]?.file.name).toBe('report.pdf')
    expect(result.notices[0]).toBe('report-copy.pdf is already selected.')
  })

  it('keeps different content that shares a filename identity path separately', async () => {
    const one = toSelectedUploadFile(createFile('a.pdf', 10, 1, 'content-a'))
    const two = toSelectedUploadFile(createFile('b.pdf', 10, 2, 'content-b'))
    const result = await dedupeSelectionByContent([one, two])
    expect(result.files).toHaveLength(2)
    expect(result.notices).toHaveLength(0)
  })

  it('enforces the batch file limit while keeping earlier selections', () => {
    const existing = Array.from({ length: MAX_BATCH_UPLOAD_FILES - 1 }, (_, index) =>
      toSelectedUploadFile(createFile(`doc-${index}.pdf`, 10, index + 1)),
    )
    const incoming = [
      createFile('extra-1.pdf', 10, 100),
      createFile('extra-2.pdf', 10, 101),
    ]

    const result = mergeUploadSelection(existing, incoming)

    expect(result.files).toHaveLength(MAX_BATCH_UPLOAD_FILES)
    expect(result.notices.join(' ')).toMatch(/up to 10 files/)
  })

  it('validates max file size per file', () => {
    const huge = new File([new Uint8Array(51 * 1024 * 1024)], 'huge.pdf', {
      type: 'application/pdf',
    })
    expect(validateDocumentFile(huge)).toMatch(/50 MB/)
  })
})
