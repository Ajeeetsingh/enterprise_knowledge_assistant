/**
 * Document viewer URL/query parameters.
 * `page` / `citeKey` drive citation navigation; large excerpt text stays out of the URL.
 */
export interface DocumentViewerParams {
  page?: number
  chunkId?: string
  /** Opaque localStorage key for citation excerpt (preferred over highlightText in URL). */
  citeKey?: string
  /** Optional short highlight query; prefer citeKey for full excerpts. */
  highlightText?: string
}

/**
 * Highlight target for the PDF canvas — text-layer matching today;
 * bounding boxes / OCR regions remain extension points.
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

export type CitationHighlightResult = 'matched' | 'failed' | 'skipped'

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
