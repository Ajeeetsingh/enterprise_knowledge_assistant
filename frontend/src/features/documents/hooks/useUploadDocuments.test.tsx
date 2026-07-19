import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DUPLICATE_DOCUMENT_USER_MESSAGE } from '@/services/errorHandler'

import * as documentApi from '../services/documentApi'
import { formatUploadBatchSummary, useUploadDocuments } from './useUploadDocuments'

vi.mock('../services/documentApi', () => ({
  uploadDocument: vi.fn(),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

/** Mirrors documentApi.uploadDocument: throws a normalised ApiError, not AxiosError. */
function duplicateApiError(filename: string, existingDocumentId?: string) {
  return {
    message: `${filename} has already been uploaded.`,
    status: 409,
    code: 'DUPLICATE_DOCUMENT',
    ...(existingDocumentId ? { existingDocumentId } : {}),
  }
}

describe('useUploadDocuments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uploads multiple files successfully', async () => {
    vi.mocked(documentApi.uploadDocument)
      .mockResolvedValueOnce({
        document_id: '1',
        filename: 'a.pdf',
        status: 'searchable',
        message: 'ok',
      })
      .mockResolvedValueOnce({
        document_id: '2',
        filename: 'b.pdf',
        status: 'searchable',
        message: 'ok',
      })

    const { result } = renderHook(() => useUploadDocuments(), {
      wrapper: createWrapper(),
    })

    let summary
    await act(async () => {
      summary = await result.current.uploadFiles([
        new File(['a'], 'a.pdf', { type: 'application/pdf' }),
        new File(['b'], 'b.pdf', { type: 'application/pdf' }),
      ])
    })

    expect(summary).toMatchObject({
      successCount: 2,
      failureCount: 0,
      duplicateCount: 0,
      total: 2,
    })
    expect(documentApi.uploadDocument).toHaveBeenCalledTimes(2)
    await waitFor(() => {
      expect(result.current.items.every((item) => item.status === 'completed')).toBe(true)
    })
  })

  it('marks server duplicates as duplicate, not failed', async () => {
    vi.mocked(documentApi.uploadDocument)
      .mockResolvedValueOnce({
        document_id: '1',
        filename: 'fresh.pdf',
        status: 'searchable',
        message: 'ok',
      })
      .mockRejectedValueOnce(duplicateApiError('exists.pdf', 'existing-doc-id'))

    const { result } = renderHook(() => useUploadDocuments(), {
      wrapper: createWrapper(),
    })

    let summary
    await act(async () => {
      summary = await result.current.uploadFiles([
        new File(['fresh'], 'fresh.pdf', { type: 'application/pdf' }),
        new File(['exists'], 'exists.pdf', { type: 'application/pdf' }),
      ])
    })

    expect(summary).toMatchObject({
      successCount: 1,
      duplicateCount: 1,
      failureCount: 0,
      total: 2,
    })
    const duplicate = result.current.items.find((item) => item.status === 'duplicate')
    expect(duplicate?.error).toBe(DUPLICATE_DOCUMENT_USER_MESSAGE)
    expect(duplicate?.existingDocumentId).toBe('existing-doc-id')
    expect(duplicate?.error).not.toBe('An unexpected error occurred.')
    expect(result.current.items.some((item) => item.status === 'failed')).toBe(false)
    expect(formatUploadBatchSummary(summary!)).toBe(
      '1 uploaded successfully · 1 already exists',
    )
  })

  it('omits existingDocumentId when the duplicate response does not authorize it', async () => {
    vi.mocked(documentApi.uploadDocument).mockRejectedValueOnce(
      duplicateApiError('secret.pdf'),
    )

    const { result } = renderHook(() => useUploadDocuments(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.uploadFiles([
        new File(['secret'], 'secret.pdf', { type: 'application/pdf' }),
      ])
    })

    const duplicate = result.current.items.find((item) => item.status === 'duplicate')
    expect(duplicate?.existingDocumentId).toBeUndefined()
  })

  it('continues after mixed success, duplicate, and genuine failure', async () => {
    vi.mocked(documentApi.uploadDocument)
      .mockResolvedValueOnce({
        document_id: '1',
        filename: 'ok.pdf',
        status: 'searchable',
        message: 'ok',
      })
      .mockRejectedValueOnce(duplicateApiError('dup.pdf'))
      .mockRejectedValueOnce({ message: 'Server error. Please try again later.', status: 500 })

    const { result } = renderHook(() => useUploadDocuments(), {
      wrapper: createWrapper(),
    })

    let summary
    await act(async () => {
      summary = await result.current.uploadFiles([
        new File(['ok'], 'ok.pdf', { type: 'application/pdf' }),
        new File(['dup'], 'dup.pdf', { type: 'application/pdf' }),
        new File(['bad'], 'bad.pdf', { type: 'application/pdf' }),
      ])
    })

    expect(summary).toMatchObject({
      successCount: 1,
      duplicateCount: 1,
      failureCount: 1,
      total: 3,
    })
    expect(formatUploadBatchSummary(summary!)).toBe(
      '1 uploaded successfully · 1 already exists · 1 failed',
    )
  })

  it('summarises an all-duplicate batch without treating it as a hard failure', async () => {
    vi.mocked(documentApi.uploadDocument)
      .mockRejectedValueOnce(duplicateApiError('a.pdf'))
      .mockRejectedValueOnce(duplicateApiError('b.pdf'))

    const { result } = renderHook(() => useUploadDocuments(), {
      wrapper: createWrapper(),
    })

    let summary
    await act(async () => {
      summary = await result.current.uploadFiles([
        new File(['a'], 'a.pdf', { type: 'application/pdf' }),
        new File(['b'], 'b.pdf', { type: 'application/pdf' }),
      ])
    })

    expect(summary).toMatchObject({
      successCount: 0,
      duplicateCount: 2,
      failureCount: 0,
    })
    expect(formatUploadBatchSummary(summary!)).toBe(
      'No new documents were uploaded. The selected documents already exist.',
    )
  })

  it('retries only genuine failed uploads, not duplicates', async () => {
    vi.mocked(documentApi.uploadDocument)
      .mockRejectedValueOnce(duplicateApiError('dup.pdf'))
      .mockRejectedValueOnce({ message: 'boom', status: 500 })
      .mockResolvedValueOnce({
        document_id: '2',
        filename: 'fail.pdf',
        status: 'searchable',
        message: 'ok',
      })

    const { result } = renderHook(() => useUploadDocuments(), {
      wrapper: createWrapper(),
    })

    await act(async () => {
      await result.current.uploadFiles([
        new File(['dup'], 'dup.pdf', { type: 'application/pdf' }),
        new File(['fail'], 'fail.pdf', { type: 'application/pdf' }),
      ])
    })

    expect(result.current.items.filter((item) => item.status === 'failed')).toHaveLength(1)
    expect(result.current.items.filter((item) => item.status === 'duplicate')).toHaveLength(1)

    await act(async () => {
      await result.current.retryFailed()
    })

    // Initial 2 calls + 1 retry for the failed file only.
    expect(documentApi.uploadDocument).toHaveBeenCalledTimes(3)
    expect(documentApi.uploadDocument).toHaveBeenLastCalledWith(
      expect.objectContaining({ name: 'fail.pdf' }),
    )
  })

  it('does not treat a non-duplicate 409 ApiError as a duplicate', async () => {
    vi.mocked(documentApi.uploadDocument).mockRejectedValueOnce({
      message: 'Document integrity check failed.',
      status: 409,
    })

    const { result } = renderHook(() => useUploadDocuments(), {
      wrapper: createWrapper(),
    })

    let summary
    await act(async () => {
      summary = await result.current.uploadFiles([
        new File(['x'], 'conflict.pdf', { type: 'application/pdf' }),
      ])
    })

    expect(summary).toMatchObject({
      successCount: 0,
      duplicateCount: 0,
      failureCount: 1,
    })
    expect(result.current.items[0]?.status).toBe('failed')
    expect(result.current.items[0]?.error).toBe('Document integrity check failed.')
  })
})
