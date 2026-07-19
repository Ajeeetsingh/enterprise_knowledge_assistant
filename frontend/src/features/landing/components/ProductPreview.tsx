import AiAvatar from '@/features/chat/components/AiAvatar'
import { ArrowUpIcon, NavIcon } from '@/components/layout/NavIcons'
import { cn } from '@/utils/cn'

const EXAMPLE_CITATIONS = [
  { source: 'Employee Handbook.pdf', page: 12 },
  { source: 'Leave Policy 2026.docx', page: 3 },
] as const

/**
 * Static product preview styled like the real chat UI.
 * No API calls — presentation only.
 */
export default function ProductPreview({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'relative mx-auto w-full max-w-3xl',
        className,
      )}
      aria-label="Product preview"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-6 -z-10 rounded-[28px] bg-[radial-gradient(ellipse_at_center,var(--accent-muted),transparent_70%)] opacity-80"
      />

      <div
        className={cn(
          'overflow-hidden rounded-[var(--radius-lg)] border border-border-default',
          'bg-surface shadow-elevation-md',
        )}
      >
        <div className="flex items-center gap-3 border-b border-border-subtle bg-surface-raised px-4 py-3">
          <div className="flex items-center gap-1.5" aria-hidden>
            <span className="size-2.5 rounded-full bg-[color-mix(in_srgb,var(--status-bad)_75%,transparent)]" />
            <span className="size-2.5 rounded-full bg-[color-mix(in_srgb,var(--status-warn)_75%,transparent)]" />
            <span className="size-2.5 rounded-full bg-[color-mix(in_srgb,var(--status-good)_75%,transparent)]" />
          </div>
          <div className="flex min-w-0 items-center gap-2 text-xs text-muted">
            <NavIcon name="chat" className="size-3.5 text-accent" />
            <span className="truncate font-medium text-foreground">Knowledge Assistant</span>
            <span className="hidden text-subtle sm:inline">· Leave policy</span>
          </div>
        </div>

        <div className="space-y-5 bg-surface px-4 py-5 sm:px-6 sm:py-6">
          <article className="flex justify-end" aria-label="Example user message">
            <div className="user-message-bubble text-sm leading-relaxed">
              What is our annual leave policy?
            </div>
          </article>

          <article className="flex items-start gap-3" aria-label="Example assistant message">
            <AiAvatar />
            <div className="ai-message-card min-w-0 flex-1 space-y-3 text-sm leading-relaxed text-foreground">
              <p>
                Employees are entitled to <strong>20 days</strong> of annual leave per calendar
                year. Leave requests should be submitted through HR with at least two weeks&apos;
                notice where possible.
              </p>

              <div>
                <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-subtle">
                  Sources
                </p>
                <ul className="flex flex-wrap gap-2">
                  {EXAMPLE_CITATIONS.map((citation) => (
                    <li
                      key={`${citation.source}-${citation.page}`}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-md border border-border-subtle',
                        'bg-overlay px-2.5 py-1.5 text-xs text-muted',
                      )}
                    >
                      <NavIcon name="documents" className="size-3.5 text-accent" />
                      <span className="font-medium text-foreground">{citation.source}</span>
                      <span className="text-subtle">p.&nbsp;{citation.page}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </article>
        </div>

        <div
          className="border-t border-border-subtle bg-surface-raised px-4 py-3 sm:px-6"
          aria-hidden
        >
          <div className="chat-input-bar pointer-events-none opacity-70">
            <span className="chat-input-field text-subtle">Ask a follow-up…</span>
            <span className="chat-send-button">
              <ArrowUpIcon className="size-4" />
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
