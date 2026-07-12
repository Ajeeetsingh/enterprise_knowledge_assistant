import type { RefObject } from 'react'

import DocumentStatusBadge from '@/features/documents/components/DocumentStatusBadge'
import { cn } from '@/utils/cn'

import {
  BackIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  DownloadIcon,
  FitWidthIcon,
  InfoPanelIcon,
  SearchIcon,
  ThumbnailsIcon,
  ZoomInIcon,
  ZoomOutIcon,
} from './ViewerIcons'

export interface DocumentViewerToolbarProps {
  filename: string
  status: string
  searchQuery: string
  onSearchQueryChange: (value: string) => void
  onSearchNext?: () => void
  onSearchPrevious?: () => void
  searchMatchLabel?: string | null
  isSearchable: boolean
  zoomPercent: number
  onZoomIn: () => void
  onZoomOut: () => void
  onFitWidth: () => void
  fitWidth: boolean
  currentPage: number
  totalPages: number
  onPageInput: (page: number) => void
  onPreviousPage: () => void
  onNextPage: () => void
  onBack: () => void
  onDownload: () => void
  isDownloading?: boolean
  thumbnailsOpen: boolean
  onToggleThumbnails: () => void
  metadataOpen: boolean
  onToggleMetadata: () => void
  searchInputRef?: RefObject<HTMLInputElement | null>
}

function ToolbarButton({
  label,
  active,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string; active?: boolean }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      aria-pressed={active}
      className={cn('viewer-tb-btn', active && 'viewer-tb-btn--active', className)}
      {...props}
    >
      {children}
    </button>
  )
}

export default function DocumentViewerToolbar({
  filename,
  status,
  searchQuery,
  onSearchQueryChange,
  onSearchNext,
  onSearchPrevious,
  searchMatchLabel,
  isSearchable,
  zoomPercent,
  onZoomIn,
  onZoomOut,
  onFitWidth,
  fitWidth,
  currentPage,
  totalPages,
  onPageInput,
  onPreviousPage,
  onNextPage,
  onBack,
  onDownload,
  isDownloading = false,
  thumbnailsOpen,
  onToggleThumbnails,
  metadataOpen,
  onToggleMetadata,
  searchInputRef,
}: DocumentViewerToolbarProps) {
  return (
    <header className="viewer-toolbar">
      {/* Left cluster: back + identity */}
      <div className="flex min-w-0 items-center gap-2">
        <ToolbarButton label="Back to documents" onClick={onBack}>
          <BackIcon />
        </ToolbarButton>

        <ToolbarButton
          label={thumbnailsOpen ? 'Hide thumbnails' : 'Show thumbnails'}
          active={thumbnailsOpen}
          className="hidden md:inline-flex"
          onClick={onToggleThumbnails}
        >
          <ThumbnailsIcon />
        </ToolbarButton>

        <div className="min-w-0 pl-1">
          <p className="viewer-title truncate">{filename}</p>
          <div className="mt-0.5 hidden sm:block">
            <DocumentStatusBadge status={status} />
          </div>
        </div>
      </div>

      {/* Center cluster: page navigation + zoom */}
      <div className="viewer-toolbar-center">
        <div className="viewer-tb-group">
          <ToolbarButton
            label="Previous page"
            onClick={onPreviousPage}
            disabled={currentPage <= 1}
          >
            <ChevronUpIcon />
          </ToolbarButton>
          <div className="viewer-page-indicator">
            <input
              type="number"
              min={1}
              max={totalPages || 1}
              value={totalPages ? currentPage : ''}
              aria-label="Current page"
              className="viewer-page-input"
              onChange={(event) => {
                const next = Number.parseInt(event.target.value, 10)
                if (Number.isFinite(next)) onPageInput(next)
              }}
            />
            <span className="viewer-page-total">/ {totalPages || '—'}</span>
          </div>
          <ToolbarButton
            label="Next page"
            onClick={onNextPage}
            disabled={totalPages > 0 && currentPage >= totalPages}
          >
            <ChevronDownIcon />
          </ToolbarButton>
        </div>

        <div className="viewer-tb-divider" aria-hidden="true" />

        <div className="viewer-tb-group">
          <ToolbarButton label="Zoom out" onClick={onZoomOut}>
            <ZoomOutIcon />
          </ToolbarButton>
          <span className="viewer-zoom-label">{zoomPercent}%</span>
          <ToolbarButton label="Zoom in" onClick={onZoomIn}>
            <ZoomInIcon />
          </ToolbarButton>
          <ToolbarButton label="Fit width" active={fitWidth} onClick={onFitWidth}>
            <FitWidthIcon />
          </ToolbarButton>
        </div>
      </div>

      {/* Right cluster: search + download + info */}
      <div className="flex items-center justify-end gap-2">
        {isSearchable && (
          <div className="viewer-search hidden lg:flex">
            <SearchIcon className="viewer-search-icon" />
            <input
              ref={searchInputRef}
              type="search"
              value={searchQuery}
              placeholder="Search document"
              aria-label="Search within document"
              className="viewer-search-input"
              onChange={(event) => onSearchQueryChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  if (event.shiftKey) onSearchPrevious?.()
                  else onSearchNext?.()
                }
              }}
            />
            {searchMatchLabel && (
              <span className="viewer-search-count">{searchMatchLabel}</span>
            )}
            <button
              type="button"
              aria-label="Previous match"
              className="viewer-search-nav"
              onClick={onSearchPrevious}
            >
              <ChevronUpIcon width={14} height={14} />
            </button>
            <button
              type="button"
              aria-label="Next match"
              className="viewer-search-nav"
              onClick={onSearchNext}
            >
              <ChevronDownIcon width={14} height={14} />
            </button>
          </div>
        )}

        <ToolbarButton
          label="Download document"
          onClick={onDownload}
          disabled={isDownloading}
        >
          <DownloadIcon />
        </ToolbarButton>

        <ToolbarButton
          label={metadataOpen ? 'Hide details' : 'Show details'}
          active={metadataOpen}
          onClick={onToggleMetadata}
        >
          <InfoPanelIcon />
        </ToolbarButton>
      </div>
    </header>
  )
}
