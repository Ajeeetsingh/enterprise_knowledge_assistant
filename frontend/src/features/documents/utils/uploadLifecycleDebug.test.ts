import { describe, expect, it } from 'vitest'

import {
  lifecycleStateFromUploadResponse,
  mapBackendStatusToLifecycleState,
} from './uploadLifecycleDebug'

describe('uploadLifecycleDebug', () => {
  it('maps backend searchable status to Completed', () => {
    expect(mapBackendStatusToLifecycleState('searchable')).toBe('Completed')
  })

  it('maps backend indexed status to Indexed', () => {
    expect(mapBackendStatusToLifecycleState('indexed')).toBe('Indexed')
  })

  it('maps backend processing status to Processing', () => {
    expect(mapBackendStatusToLifecycleState('processing')).toBe('Processing')
  })

  it('maps backend failure statuses to Failed', () => {
    expect(mapBackendStatusToLifecycleState('failed')).toBe('Failed')
    expect(mapBackendStatusToLifecycleState('failed_embedding')).toBe('Failed')
  })

  it('maps upload API responses to lifecycle states', () => {
    expect(
      lifecycleStateFromUploadResponse({
        document_id: 'doc-1',
        filename: 'policy.pdf',
        status: 'searchable',
        message: 'ready',
      }),
    ).toBe('Completed')

    expect(
      lifecycleStateFromUploadResponse({
        document_id: 'doc-2',
        filename: 'policy.pdf',
        status: 'processing',
        message: 'processing',
      }),
    ).toBe('Processing')
  })
})
