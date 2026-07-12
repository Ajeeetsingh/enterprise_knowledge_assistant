import { useCallback, useReducer } from 'react'

import { clampZoom } from '../utils/zoomMath'
import type { DocumentViewerState, ZoomIntent } from '../types'

type ViewerAction =
  | { type: 'commit_zoom'; zoom: number; fitWidth: boolean }
  | { type: 'request_zoom'; intentType: ZoomIntent['type'] }
  | { type: 'set_current_page'; page: number }
  | { type: 'set_total_pages'; total: number }
  | { type: 'toggle_thumbnails' }
  | { type: 'set_thumbnails_open'; open: boolean }
  | { type: 'toggle_metadata' }
  | { type: 'set_metadata_open'; open: boolean }
  | { type: 'set_search_query'; query: string }

const initialState: DocumentViewerState = {
  zoom: 1,
  fitWidth: true,
  zoomIntent: null,
  currentPage: 1,
  totalPages: 0,
  thumbnailsOpen: true,
  metadataOpen: false,
  searchQuery: '',
}

function reducer(state: DocumentViewerState, action: ViewerAction): DocumentViewerState {
  switch (action.type) {
    case 'commit_zoom':
      return { ...state, zoom: clampZoom(action.zoom), fitWidth: action.fitWidth }
    case 'request_zoom':
      return {
        ...state,
        zoomIntent: { type: action.intentType, nonce: (state.zoomIntent?.nonce ?? 0) + 1 },
      }
    case 'set_current_page':
      return { ...state, currentPage: Math.max(1, action.page) }
    case 'set_total_pages':
      return { ...state, totalPages: action.total }
    case 'toggle_thumbnails':
      return { ...state, thumbnailsOpen: !state.thumbnailsOpen }
    case 'set_thumbnails_open':
      return { ...state, thumbnailsOpen: action.open }
    case 'toggle_metadata':
      return { ...state, metadataOpen: !state.metadataOpen }
    case 'set_metadata_open':
      return { ...state, metadataOpen: action.open }
    case 'set_search_query':
      return { ...state, searchQuery: action.query }
    default:
      return state
  }
}

/**
 * Owns the document viewer's UI state.
 *
 * Zoom is split into two concerns:
 * - `state.zoom` / `state.fitWidth` — the *committed* render scale, the single
 *   source of truth used to size `<Page>` and to display the zoom % in the
 *   toolbar.
 * - `state.zoomIntent` — a one-shot trigger consumed by `usePdfZoomGestures`
 *   (inside `DocumentPdfViewer`) for discrete button/keyboard zoom actions,
 *   which need access to the scroll container to animate smoothly and keep
 *   the viewport anchored. Continuous gestures (ctrl+wheel, pinch) are
 *   handled entirely inside that hook and call `commitZoom` directly.
 */
export function useDocumentViewerState() {
  const [state, dispatch] = useReducer(reducer, initialState)

  const commitZoom = useCallback(
    (zoom: number, fitWidth: boolean) => dispatch({ type: 'commit_zoom', zoom, fitWidth }),
    [],
  )
  const requestZoomIn = useCallback(() => dispatch({ type: 'request_zoom', intentType: 'in' }), [])
  const requestZoomOut = useCallback(
    () => dispatch({ type: 'request_zoom', intentType: 'out' }),
    [],
  )
  const requestFitWidth = useCallback(
    () => dispatch({ type: 'request_zoom', intentType: 'fit' }),
    [],
  )
  const requestActualSize = useCallback(
    () => dispatch({ type: 'request_zoom', intentType: 'actual' }),
    [],
  )
  const setCurrentPage = useCallback(
    (page: number) => dispatch({ type: 'set_current_page', page }),
    [],
  )
  const setTotalPages = useCallback(
    (total: number) => dispatch({ type: 'set_total_pages', total }),
    [],
  )
  const toggleThumbnails = useCallback(() => dispatch({ type: 'toggle_thumbnails' }), [])
  const setThumbnailsOpen = useCallback(
    (open: boolean) => dispatch({ type: 'set_thumbnails_open', open }),
    [],
  )
  const toggleMetadata = useCallback(() => dispatch({ type: 'toggle_metadata' }), [])
  const setMetadataOpen = useCallback(
    (open: boolean) => dispatch({ type: 'set_metadata_open', open }),
    [],
  )
  const setSearchQuery = useCallback(
    (query: string) => dispatch({ type: 'set_search_query', query }),
    [],
  )

  return {
    state,
    commitZoom,
    requestZoomIn,
    requestZoomOut,
    requestFitWidth,
    requestActualSize,
    setCurrentPage,
    setTotalPages,
    toggleThumbnails,
    setThumbnailsOpen,
    toggleMetadata,
    setMetadataOpen,
    setSearchQuery,
  }
}
