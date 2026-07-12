/**
 * Shared client-side "save this blob as a file" helper. Used by any feature
 * that generates a downloadable artifact in the browser (document preview
 * downloads, conversation export, report export, ...).
 */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
