import { Document, Page } from 'react-pdf'

import { cn } from '@/utils/cn'

import '../pdfWorker'
import { CloseIcon } from './ViewerIcons'

export interface DocumentThumbnailSidebarProps {
  fileUrl: string
  totalPages: number
  currentPage: number
  isOpen: boolean
  onClose: () => void
  onSelectPage: (page: number) => void
  /** Renders as an overlay drawer on small screens. */
  asOverlay?: boolean
  className?: string
}

export default function DocumentThumbnailSidebar({
  fileUrl,
  totalPages,
  currentPage,
  isOpen,
  onClose,
  onSelectPage,
  asOverlay = false,
  className,
}: DocumentThumbnailSidebarProps) {
  return (
    <aside
      aria-label="Page thumbnails"
      aria-hidden={!isOpen}
      className={cn(
        'viewer-thumbnails',
        asOverlay ? 'viewer-thumbnails--overlay' : 'viewer-thumbnails--inline',
        isOpen ? 'viewer-thumbnails--open' : 'viewer-thumbnails--closed',
        className,
      )}
    >
      <div className="viewer-thumbnails-head">
        <span className="viewer-thumbnails-title">Pages</span>
        <button
          type="button"
          aria-label="Hide thumbnails"
          className="viewer-tb-btn viewer-tb-btn--sm"
          onClick={onClose}
        >
          <CloseIcon width={16} height={16} />
        </button>
      </div>

      <div className="viewer-thumbnails-list scrollbar-thin">
        {isOpen && (
          <Document file={fileUrl} loading={null} error={null}>
            {Array.from({ length: totalPages }, (_, index) => {
              const pageNumber = index + 1
              const isActive = pageNumber === currentPage
              return (
                <button
                  key={pageNumber}
                  type="button"
                  className={cn(
                    'viewer-thumbnail',
                    isActive && 'viewer-thumbnail--active',
                  )}
                  onClick={() => onSelectPage(pageNumber)}
                  aria-label={`Go to page ${pageNumber}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <div className="viewer-thumbnail-canvas">
                    <Page
                      pageNumber={pageNumber}
                      width={132}
                      renderTextLayer={false}
                      renderAnnotationLayer={false}
                      loading={<div className="viewer-thumbnail-skeleton" />}
                    />
                  </div>
                  <span className="viewer-thumbnail-label">{pageNumber}</span>
                </button>
              )
            })}
          </Document>
        )}
      </div>
    </aside>
  )
}
