import type { AnchorHTMLAttributes, PropsWithChildren } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'

import { cn } from '@/utils/cn'

import 'highlight.js/styles/github.css'

export interface MarkdownRendererProps {
  content: string
  className?: string
}

const DISALLOWED_ELEMENTS = [
  'script',
  'iframe',
  'object',
  'embed',
  'form',
  'input',
  'button',
  'style',
] as const

function isSafeHref(href: string | undefined): href is string {
  if (!href) return false

  const trimmed = href.trim()
  if (trimmed.startsWith('#') || trimmed.startsWith('/')) {
    return true
  }

  try {
    const parsed = new URL(trimmed)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' || parsed.protocol === 'mailto:'
  } catch {
    return false
  }
}

function MarkdownLink({
  href,
  children,
  className,
  ...props
}: PropsWithChildren<AnchorHTMLAttributes<HTMLAnchorElement>>) {
  if (!isSafeHref(href)) {
    return <span className={className}>{children}</span>
  }

  const isExternal = href.startsWith('http://') || href.startsWith('https://')

  return (
    <a
      href={href}
      className={cn(
        'font-medium text-primary-600 underline underline-offset-2 hover:text-primary-700',
        'dark:text-primary-400 dark:hover:text-primary-300',
        className,
      )}
      {...(isExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      {...props}
    >
      {children}
    </a>
  )
}

const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="mb-3 mt-4 text-xl font-bold first:mt-0">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-2 mt-4 text-lg font-semibold first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-2 mt-3 text-base font-semibold first:mt-0">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="mb-2 mt-3 text-sm font-semibold first:mt-0">{children}</h4>
  ),
  h5: ({ children }) => (
    <h5 className="mb-1 mt-2 text-sm font-medium first:mt-0">{children}</h5>
  ),
  h6: ({ children }) => (
    <h6 className="mb-1 mt-2 text-xs font-medium uppercase tracking-wide first:mt-0">
      {children}
    </h6>
  ),
  p: ({ children }) => <p className="my-2 break-words first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="break-words">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-3 border-l-4 border-neutral-300 pl-4 italic text-neutral-600 dark:border-neutral-600 dark:text-neutral-300">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-neutral-200 dark:border-neutral-700" />,
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto">
      <table className="min-w-full border-collapse text-left text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800/60">
      {children}
    </thead>
  ),
  tbody: ({ children }) => <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">{children}</tbody>,
  tr: ({ children }) => <tr>{children}</tr>,
  th: ({ children }) => (
    <th className="px-3 py-2 font-semibold text-neutral-900 dark:text-neutral-100">{children}</th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 align-top text-neutral-700 dark:text-neutral-200">{children}</td>
  ),
  pre: ({ children }) => (
    <pre className="hljs my-3 overflow-x-auto rounded-md border border-neutral-200 bg-neutral-950 p-3 text-sm dark:border-neutral-700">
      {children}
    </pre>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className?.includes('language-'))

    if (isBlock) {
      return (
        <code className={cn('font-mono text-[0.875em]', className)} {...props}>
          {children}
        </code>
      )
    }

    return (
      <code
        className="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-[0.85em] text-neutral-800 dark:bg-neutral-800 dark:text-neutral-100"
        {...props}
      >
        {children}
      </code>
    )
  },
  a: MarkdownLink,
}

export default function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn('markdown-body break-words text-sm leading-relaxed', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        disallowedElements={[...DISALLOWED_ELEMENTS]}
        unwrapDisallowed
        skipHtml
        urlTransform={(url) => (isSafeHref(url) ? url : '')}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
