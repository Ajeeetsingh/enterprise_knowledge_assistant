import { describe, expect, it, vi } from 'vitest'

import apiClient from '@/services/api'
import { uploadDocument } from '@/features/documents/services/documentApi'

describe('apiClient multipart uploads', () => {
  it('does not force application/json Content-Type for FormData requests', async () => {
    const formData = new FormData()
    formData.append('file', new File(['Annual leave policy'], 'policy.txt', { type: 'text/plain' }))

    let capturedContentType: string | undefined = 'unset'

    apiClient.defaults.adapter = vi.fn(async (config) => {
      capturedContentType = config.headers['Content-Type'] as string | undefined
      return {
        data: {
          document_id: '11111111-1111-1111-1111-111111111111',
          filename: 'policy.txt',
          status: 'searchable',
          message: 'Uploaded.',
        },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    })

    await apiClient.post('/documents/upload', formData)

    expect(capturedContentType).not.toBe('application/json')
    expect(formData.get('file')).toBeInstanceOf(File)
  })
})

describe('uploadDocument', () => {
  it('posts FormData with the backend file field name', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
      data: {
        document_id: '11111111-1111-1111-1111-111111111111',
        filename: 'policy.txt',
        status: 'searchable',
        message: 'Uploaded.',
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    })

    const file = new File(['Annual leave policy'], 'policy.txt', { type: 'text/plain' })
    await uploadDocument(file)

    expect(post).toHaveBeenCalledWith('/documents/upload', expect.any(FormData))
    const formData = post.mock.calls[0]?.[1] as FormData
    expect(formData.get('file')).toBe(file)

    post.mockRestore()
  })
})
