import { describe, expect, it } from 'vitest'

import { DocumentStatus } from '@/features/documents/types'

import { getUploadDisplayStatus, shouldPollRecentUploads } from './uploadStatus'

describe('uploadStatus', () => {
  it('maps backend statuses to upload display statuses', () => {
    expect(getUploadDisplayStatus(DocumentStatus.Searchable)).toBe('READY')
    expect(getUploadDisplayStatus(DocumentStatus.Processing)).toBe('PROCESSING')
    expect(getUploadDisplayStatus(DocumentStatus.Failed)).toBe('FAILED')
    expect(getUploadDisplayStatus(DocumentStatus.Searchable, true)).toBe('UPLOADING')
  })

  it('polls while processing documents remain', () => {
    expect(
      shouldPollRecentUploads([
        { status: DocumentStatus.Searchable },
        { status: DocumentStatus.Processing },
      ]),
    ).toBe(true)

    expect(
      shouldPollRecentUploads([
        { status: DocumentStatus.Searchable },
        { status: DocumentStatus.Failed },
      ]),
    ).toBe(false)
  })
})
