import { useCallback, useEffect, useRef, useState } from 'react'

import { useMinWidthMediaQuery } from '@/hooks/useMinWidthMediaQuery'
import type { DocumentDetail } from '@/features/documents/types'

import { useDocumentViewerHighlightTarget } from '../hooks/useDocumentViewerParams'
import { useDocumentViewerState } from '../hooks/useDocumentViewerState'
import { usePdfKeyboardShortcuts } from '../hooks/usePdfKeyboardShortcuts'
import { usePdfTextSearch, type SearchablePdfDocument } from '../hooks/usePdfTextSearch'
import DocumentMetadataPanel from './DocumentMetadataPanel'
import DocumentPdfViewer from './DocumentPdfViewer'
import DocumentThumbnailSidebar from './DocumentThumbnailSidebar'
import DocumentViewerToolbar from './DocumentViewerToolbar'
import ViewerDrawer from './ViewerDrawer'
import { ChevronDownIcon, ChevronUpIcon, DownloadIcon } from './ViewerIcons'

const TABLET_MIN = 768

export interface DocumentViewerLayoutProps {
  detail: DocumentDetail
  fileUrl: string
  isPdf: boolean
  onBack: () => void
  onDownload: () => void
  isDownloading?: boolean
}

export default function DocumentViewerLayout({
  detail,
  fileUrl,
  isPdf,
  onBack,
  onDownload,
  isDownloading = false,
}: DocumentViewerLayoutProps) {
  const highlightTarget = useDocumentViewerHighlightTarget()
  const isTabletUp = useMinWidthMediaQuery(TABLET_MIN)

  const {
    state,
    commitZoom,
    requestZoomIn,
    requestZoomOut,
    requestFitWidth,
    requestActualSize,
    setCurrentPage,
    setTotalPages,
    setThumbnailsOpen,
    toggleThumbnails,
    toggleMetadata,
    setMetadataOpen,
    setSearchQuery,
  } = useDocumentViewerState()

  const [pdfProxy, setPdfProxy] = useState<SearchablePdfDocument | null>(null)
  const [pageCount, setPageCount] = useState<number | null>(null)
  const [scrollTargetPage, setScrollTargetPage] = useState<number | null>(null)
  const [citationHighlightNotice, setCitationHighlightNotice] = useState<string | null>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  const search = usePdfTextSearch(pdfProxy, state.searchQuery)

  // Default thumbnails open on tablet+ and closed on mobile.
  useEffect(() => {
    setThumbnailsOpen(isTabletUp)
  }, [isTabletUp, setThumbnailsOpen])

  useEffect(() => {
    setCitationHighlightNotice(null)
  }, [highlightTarget?.page, highlightTarget?.highlightText])

  const handleCitationHighlightResult = useCallback(
    (result: 'matched' | 'failed' | 'skipped') => {
      if (result === 'failed' && highlightTarget?.highlightText) {
        setCitationHighlightNotice(
          'Source page opened. The exact cited passage could not be highlighted.',
        )
      }
    },
    [highlightTarget?.highlightText],
  )

  const zoomPercent = state.fitWidth ? 100 : Math.round(state.zoom * 100)

  const handleDocumentLoad = useCallback(
    (pdf: SearchablePdfDocument, numPages: number) => {
      setPdfProxy(pdf)
      setPageCount(numPages)
      setTotalPages(numPages)
      if (highlightTarget?.page && highlightTarget.page <= numPages) {
        setCurrentPage(highlightTarget.page)
        setScrollTargetPage(highlightTarget.page)
      }
    },
    [highlightTarget?.page, setCurrentPage, setTotalPages],
  )

  const goToPage = useCallback(
    (page: number) => {
      const clamped = Math.min(Math.max(page, 1), Math.max(state.totalPages, 1))
      setCurrentPage(clamped)
      setScrollTargetPage(clamped)
    },
    [setCurrentPage, state.totalPages],
  )

  const handleNextPage = useCallback(
    () => goToPage(state.currentPage + 1),
    [goToPage, state.currentPage],
  )
  const handlePreviousPage = useCallback(
    () => goToPage(state.currentPage - 1),
    [goToPage, state.currentPage],
  )

  const toggleFitWidth = useCallback(() => {
    if (state.fitWidth) requestActualSize()
    else requestFitWidth()
  }, [state.fitWidth, requestActualSize, requestFitWidth])

  usePdfKeyboardShortcuts({
    onNextPage: handleNextPage,
    onPreviousPage: handlePreviousPage,
    onZoomIn: requestZoomIn,
    onZoomOut: requestZoomOut,
    onFitWidth: toggleFitWidth,
    onFocusSearch: () => searchInputRef.current?.focus(),
    enabled: isPdf,
  })

  function handleSearchNext() {
    const match = search.goToNextMatch()
    if (match) goToPage(match.pageNumber)
  }

  function handleSearchPrevious() {
    const match = search.goToPreviousMatch()
    if (match) goToPage(match.pageNumber)
  }

  const searchMatchLabel =
    state.searchQuery.trim() && search.matches.length > 0
      ? `${search.activeMatchIndex + 1}/${search.matches.length}`
      : state.searchQuery.trim() && !search.isSearching
        ? '0/0'
        : null

  function handleSelectThumbnail(page: number) {
    goToPage(page)
    if (!isTabletUp) setThumbnailsOpen(false)
  }

  return (
    <div className="viewer-shell">
      <DocumentViewerToolbar
        filename={detail.filename}
        status={detail.status}
        searchQuery={state.searchQuery}
        onSearchQueryChange={setSearchQuery}
        onSearchNext={handleSearchNext}
        onSearchPrevious={handleSearchPrevious}
        searchMatchLabel={searchMatchLabel}
        isSearchable={isPdf}
        zoomPercent={zoomPercent}
        onZoomIn={requestZoomIn}
        onZoomOut={requestZoomOut}
        onFitWidth={toggleFitWidth}
        fitWidth={state.fitWidth}
        currentPage={state.currentPage}
        totalPages={state.totalPages}
        onPageInput={goToPage}
        onPreviousPage={handlePreviousPage}
        onNextPage={handleNextPage}
        onBack={onBack}
        onDownload={onDownload}
        isDownloading={isDownloading}
        thumbnailsOpen={state.thumbnailsOpen}
        onToggleThumbnails={toggleThumbnails}
        metadataOpen={state.metadataOpen}
        onToggleMetadata={toggleMetadata}
        searchInputRef={searchInputRef}
      />

      <div className="viewer-body">
        {isPdf && (
          <DocumentThumbnailSidebar
            fileUrl={fileUrl}
            totalPages={state.totalPages}
            currentPage={state.currentPage}
            isOpen={state.thumbnailsOpen}
            onClose={() => setThumbnailsOpen(false)}
            onSelectPage={handleSelectThumbnail}
            asOverlay={!isTabletUp}
          />
        )}

        <main className="viewer-canvas-region">
          {citationHighlightNotice && (
            <div className="viewer-citation-notice" role="status">
              {citationHighlightNotice}
            </div>
          )}
          {isPdf ? (
            <DocumentPdfViewer
              fileUrl={fileUrl}
              currentPage={state.currentPage}
              zoom={state.zoom}
              fitWidth={state.fitWidth}
              onDocumentLoad={handleDocumentLoad}
              onVisiblePageChange={setCurrentPage}
              onGoToPage={goToPage}
              scrollTargetPage={scrollTargetPage}
              highlightTarget={highlightTarget}
              onCitationHighlightResult={handleCitationHighlightResult}
              zoomIntent={state.zoomIntent}
              onZoomCommit={commitZoom}
            />
          ) : (
            <div className="viewer-nonpdf">
              <p className="viewer-nonpdf-text">
                In-app preview is available for PDF documents. Download this file to open it
                locally.
              </p>
              <button type="button" className="viewer-primary-btn" onClick={onDownload}>
                <DownloadIcon />
                Download {detail.filename}
              </button>
            </div>
          )}
        </main>

        {/* Metadata: collapsible right-side drawer (overlay keeps canvas dominant). */}
        <ViewerDrawer
          isOpen={state.metadataOpen}
          onClose={() => setMetadataOpen(false)}
          title="Document details"
          side="right"
          overlay
        >
          <DocumentMetadataPanel detail={detail} pageCount={pageCount} />
        </ViewerDrawer>
      </div>

      {/* Mobile page navigation bar */}
      {isPdf && (
        <div className="viewer-mobile-bar md:hidden">
          <button
            type="button"
            aria-label="Previous page"
            className="viewer-tb-btn"
            onClick={handlePreviousPage}
            disabled={state.currentPage <= 1}
          >
            <ChevronUpIcon />
          </button>
          <span className="viewer-mobile-pages">
            {state.totalPages ? `${state.currentPage} / ${state.totalPages}` : '—'}
          </span>
          <button
            type="button"
            aria-label="Next page"
            className="viewer-tb-btn"
            onClick={handleNextPage}
            disabled={state.totalPages > 0 && state.currentPage >= state.totalPages}
          >
            <ChevronDownIcon />
          </button>
        </div>
      )}
    </div>
  )
}
