/**
 * Document viewer URL/query parameters.
 * `page` is implemented today; chunk and text highlight are extension points.
 */
export interface DocumentViewerParams {
  page?: number
  chunkId?: string
  highlightText?: string
}

/**
 * Future highlight target — bounding boxes and OCR regions can be added without
 * changing the viewer shell.
 */
export interface DocumentViewerHighlightTarget {
  page: number
  chunkId?: string
  highlightText?: string
  /** Reserved for chunk boundary overlays. */
  chunkBoundaries?: never
  /** Reserved for paragraph-level highlights. */
  paragraphRegions?: never
  /** Reserved for OCR bounding boxes. */
  ocrRegions?: never
}

/**
 * One-shot trigger for discrete (button/keyboard) zoom actions.
 * `nonce` changes on every request so the effect that consumes it can fire
 * even when the same `type` is requested twice in a row.
 */
export interface ZoomIntent {
  type: 'in' | 'out' | 'fit' | 'actual'
  nonce: number
}

export interface DocumentViewerState {
  zoom: number
  fitWidth: boolean
  zoomIntent: ZoomIntent | null
  currentPage: number
  totalPages: number
  thumbnailsOpen: boolean
  metadataOpen: boolean
  searchQuery: string
}

export interface PdfSearchMatch {
  pageNumber: number
  matchIndex: number
}
