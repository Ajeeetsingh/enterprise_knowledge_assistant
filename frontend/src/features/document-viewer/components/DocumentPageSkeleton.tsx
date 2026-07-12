import type { CSSProperties } from 'react'

import { cn } from '@/utils/cn'

export default function DocumentPageSkeleton({
  className,
  style,
}: {
  className?: string
  style?: CSSProperties
}) {
  return (
    <div
      className={cn(
        'document-page-skeleton relative overflow-hidden rounded-md bg-[var(--bg-overlay)]',
        className,
      )}
      style={style}
      aria-hidden="true"
    >
      <div className="document-page-skeleton__shimmer absolute inset-0" />
    </div>
  )
}
