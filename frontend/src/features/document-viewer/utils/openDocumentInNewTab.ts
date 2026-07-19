/**
 * Open a same-origin viewer path in a new tab with noopener/noreferrer semantics.
 */
export function openDocumentInNewTab(path: string): void {
  const href =
    path.startsWith('http://') || path.startsWith('https://')
      ? path
      : `${window.location.origin}${path.startsWith('/') ? path : `/${path}`}`

  const anchor = document.createElement('a')
  anchor.href = href
  anchor.target = '_blank'
  anchor.rel = 'noopener noreferrer'
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
