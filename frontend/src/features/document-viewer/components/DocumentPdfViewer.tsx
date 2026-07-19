import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'

import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

import { usePdfZoomGestures } from '../hooks/usePdfZoomGestures'
import type { SearchablePdfDocument } from '../hooks/usePdfTextSearch'
import '../pdfWorker'
import type { CitationHighlightResult, DocumentViewerHighlightTarget, ZoomIntent } from '../types'
import {
  findPageTextLayer,
  highlightCitationInTextLayer,
} from '../utils/applyTextLayerHighlight'
import { computeRenderWidth } from '../utils/zoomMath'
import DocumentPageSkeleton from './DocumentPageSkeleton'

const CANVAS_HORIZONTAL_PADDING = 48
const FIT_WIDTH_MAX = 1000

export interface DocumentPdfViewerProps {
  fileUrl: string
  currentPage: number
  zoom: number
  fitWidth: boolean
  onDocumentLoad: (pdf: SearchablePdfDocument, numPages: number) => void
  onVisiblePageChange: (page: number) => void
  onGoToPage: (page: number) => void
  scrollTargetPage?: number | null
  highlightTarget?: DocumentViewerHighlightTarget | null
  /** Reports citation text-highlight outcome (progressive enhancement). */
  onCitationHighlightResult?: (result: CitationHighlightResult) => void
  /** One-shot trigger for toolbar/keyboard zoom actions (see `usePdfZoomGestures`). */
  zoomIntent?: ZoomIntent | null
  /** Commits a new zoom/fitWidth value back to the viewer's source of truth. */
  onZoomCommit: (zoom: number, fitWidth: boolean) => void
}

export default function DocumentPdfViewer({
  fileUrl,
  currentPage,
  zoom,
  fitWidth,
  onDocumentLoad,
  onVisiblePageChange,
  onGoToPage,
  scrollTargetPage,
  highlightTarget,
  onCitationHighlightResult,
  zoomIntent,
  onZoomCommit,
}: DocumentPdfViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const [numPages, setNumPages] = useState(0)
  const [pdfProxy, setPdfProxy] = useState<SearchablePdfDocument | null>(null)
  const [availableWidth, setAvailableWidth] = useState(0)
  const touchStartX = useRef<number | null>(null)
  const activeTouchCount = useRef(0)
  const pendingScrollPage = useRef<number | null>(null)
  const lastHighlightKey = useRef<string | null>(null)
  const highlightAttemptedFor = useRef<string | null>(null)

  useLayoutEffect(() => {
    const node = scrollRef.current
    if (!node) return

    const measure = () => setAvailableWidth(node.clientWidth)
    measure()

    const observer = new ResizeObserver(measure)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const basePageWidth = Math.max(280, availableWidth - CANVAS_HORIZONTAL_PADDING)
  const pageWidth = computeRenderWidth(basePageWidth, zoom, fitWidth, FIT_WIDTH_MAX)

  const computeRenderWidthForZoom = useCallback(
    (candidateZoom: number, candidateFitWidth: boolean) =>
      computeRenderWidth(basePageWidth, candidateZoom, candidateFitWidth, FIT_WIDTH_MAX),
    [basePageWidth],
  )

  const { previewStyle } = usePdfZoomGestures({
    containerRef: scrollRef,
    zoom,
    fitWidth,
    renderWidth: pageWidth,
    computeRenderWidth: computeRenderWidthForZoom,
    zoomIntent: zoomIntent ?? null,
    onCommit: onZoomCommit,
    enabled: true,
  })

  const pagesWrapperStyle = useMemo(
    () => ({ ...previewStyle, willChange: previewStyle.transform ? 'transform' : undefined }),
    [previewStyle],
  )

  const scrollToPage = useCallback((page: number, behavior: ScrollBehavior = 'smooth') => {
    const element = pageRefs.current.get(page)
    if (element) {
      element.scrollIntoView({ behavior, block: 'start' })
      pendingScrollPage.current = null
    } else {
      pendingScrollPage.current = page
    }
  }, [])

  const registerPageRef = useCallback((page: number, element: HTMLDivElement | null) => {
    if (element) {
      pageRefs.current.set(page, element)
      if (pendingScrollPage.current === page) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        pendingScrollPage.current = null
      }
    } else {
      pageRefs.current.delete(page)
    }
  }, [])

  // Citation / RAG entry point: scroll to the cited page once the doc is ready.
  useEffect(() => {
    if (highlightTarget?.page) {
      scrollToPage(highlightTarget.page)
    }
  }, [
    highlightTarget?.page,
    highlightTarget?.chunkId,
    highlightTarget?.highlightText,
    numPages,
    scrollToPage,
  ])

  useEffect(() => {
    if (scrollTargetPage) {
      scrollToPage(scrollTargetPage)
    }
  }, [scrollTargetPage, scrollToPage])

  // Re-apply highlights after zoom/layout rebuilds the text layer.
  useEffect(() => {
    lastHighlightKey.current = null
  }, [pageWidth])

  // Progressive enhancement: match citation excerpt against the cited page text layer only.
  useEffect(() => {
    const page = highlightTarget?.page
    const excerpt = highlightTarget?.highlightText?.trim()
    if (!page || !excerpt || numPages === 0) {
      return
    }

    const highlightKey = `${page}::${excerpt}`
    if (lastHighlightKey.current === highlightKey) {
      return
    }

    let cancelled = false
    let tries = 0

    const attempt = (): boolean => {
      if (cancelled) return true
      const frame = pageRefs.current.get(page)
      if (!frame) return false
      const textLayer = findPageTextLayer(frame)
      if (!textLayer || textLayer.querySelectorAll('span').length === 0) {
        return false
      }

      const result = highlightCitationInTextLayer(textLayer, excerpt)
      lastHighlightKey.current = highlightKey
      highlightAttemptedFor.current = highlightKey
      onCitationHighlightResult?.(result)
      return true
    }

    if (attempt()) {
      return () => {
        cancelled = true
      }
    }

    const timer = window.setInterval(() => {
      tries += 1
      if (attempt() || tries >= 25) {
        window.clearInterval(timer)
        if (
          !cancelled &&
          tries >= 25 &&
          highlightAttemptedFor.current !== highlightKey
        ) {
          highlightAttemptedFor.current = highlightKey
          onCitationHighlightResult?.('failed')
        }
      }
    }, 120)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [
    highlightTarget?.page,
    highlightTarget?.highlightText,
    numPages,
    pageWidth,
    onCitationHighlightResult,
  ])

  useEffect(() => {
    const root = scrollRef.current
    if (!root || numPages === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)

        const top = visible[0]
        if (!top?.target) return
        const page = Number((top.target as HTMLElement).dataset.page)
        if (Number.isFinite(page)) {
          onVisiblePageChange(page)
        }
      },
      { root, threshold: [0.35, 0.55, 0.75] },
    )

    pageRefs.current.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [numPages, onVisiblePageChange])

  // Single-finger swipe-to-change-page. Guarded against multi-touch so it
  // never fires alongside the two-finger pinch-to-zoom gesture above.
  function handleTouchStart(event: React.TouchEvent) {
    activeTouchCount.current = event.touches.length
    touchStartX.current = event.touches.length === 1 ? event.touches[0]?.clientX ?? null : null
  }

  function handleTouchEnd(event: React.TouchEvent) {
    const wasSingleTouch = activeTouchCount.current === 1
    activeTouchCount.current = event.touches.length
    const startX = touchStartX.current
    touchStartX.current = null
    if (!wasSingleTouch || startX == null) return

    const endX = event.changedTouches[0]?.clientX
    if (endX == null) return

    const delta = endX - startX
    if (Math.abs(delta) < 48) return

    if (delta < 0 && currentPage < numPages) {
      onGoToPage(currentPage + 1)
      scrollToPage(currentPage + 1)
    } else if (delta > 0 && currentPage > 1) {
      onGoToPage(currentPage - 1)
      scrollToPage(currentPage - 1)
    }
  }

  return (
    <div
      ref={scrollRef}
      className="document-pdf-canvas min-h-0 flex-1 overflow-auto scroll-smooth scrollbar-thin"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className="document-pdf-pages" style={pagesWrapperStyle}>
        <Document
          file={fileUrl}
          loading={
            <div className="flex items-start justify-center py-10">
              <DocumentPageSkeleton
                className="w-full max-w-3xl"
                style={{ height: 'min(78vh, 900px)' }}
              />
            </div>
          }
          error={
            <div className="flex items-center justify-center py-16">
              <p role="alert" className="text-sm text-[var(--status-bad)]">
                This document could not be displayed.
              </p>
            </div>
          }
          onLoadSuccess={(pdf) => {
            const searchable = pdf as SearchablePdfDocument
            setPdfProxy(searchable)
            setNumPages(pdf.numPages)
            onDocumentLoad(searchable, pdf.numPages)
          }}
          onLoadError={(error) => {
            console.error('[document-viewer] PDF load failed', error)
          }}
          className="flex flex-col items-center gap-6 px-4 py-6 md:px-6 md:py-8"
        >
          {availableWidth > 0 &&
            Array.from({ length: numPages }, (_, index) => {
              const pageNumber = index + 1
              const isActive = pageNumber === currentPage
              return (
                <div
                  key={pageNumber}
                  ref={(element) => registerPageRef(pageNumber, element)}
                  data-page={pageNumber}
                  data-active={isActive || undefined}
                  className="document-page-frame relative"
                  style={{ width: pageWidth }}
                >
                  <Page
                    pageNumber={pageNumber}
                    width={pageWidth}
                    renderTextLayer
                    renderAnnotationLayer
                    loading={
                      <DocumentPageSkeleton
                        className="w-full"
                        style={{ height: pageWidth * 1.3 }}
                      />
                    }
                  />
                  <span className="document-page-number">{pageNumber}</span>
                </div>
              )
            })}
        </Document>
      </div>

      {highlightTarget && pdfProxy && (
        <span className="sr-only" data-viewer-highlight-ready="true">
          Highlight target page {highlightTarget.page}
        </span>
      )}
    </div>
  )
}

void pdfjs
