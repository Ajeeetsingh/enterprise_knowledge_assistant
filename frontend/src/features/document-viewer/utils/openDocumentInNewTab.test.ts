import { beforeEach, describe, expect, it, vi } from 'vitest'

import { openDocumentInNewTab } from './openDocumentInNewTab'

describe('openDocumentInNewTab', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

  it('opens a same-origin path with target=_blank and noopener noreferrer', () => {
    const created: HTMLAnchorElement[] = []
    const nativeCreate = document.createElement.bind(document)

    vi.spyOn(document, 'createElement').mockImplementation(((tagName: string) => {
      const el = nativeCreate(tagName)
      if (tagName.toLowerCase() === 'a') {
        created.push(el as HTMLAnchorElement)
        el.click = vi.fn()
        el.remove = vi.fn()
      }
      return el
    }) as typeof document.createElement)

    openDocumentInNewTab('/documents/doc-123?page=14&citeKey=abc')

    expect(created).toHaveLength(1)
    expect(created[0]?.target).toBe('_blank')
    expect(created[0]?.rel).toBe('noopener noreferrer')
    expect(created[0]?.getAttribute('href') ?? created[0]?.href).toContain(
      '/documents/doc-123?page=14&citeKey=abc',
    )
    expect(created[0]?.click).toHaveBeenCalledTimes(1)
  })
})
