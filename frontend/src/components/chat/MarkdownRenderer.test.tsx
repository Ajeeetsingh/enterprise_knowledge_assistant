import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import MarkdownRenderer from './MarkdownRenderer'

describe('MarkdownRenderer', () => {
  it('renders headings', () => {
    render(<MarkdownRenderer content={'# Main Title\n\n## Sub Title'} />)

    expect(screen.getByRole('heading', { level: 1, name: 'Main Title' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Sub Title' })).toBeInTheDocument()
  })

  it('renders ordered and unordered lists', () => {
    const { container } = render(
      <MarkdownRenderer
        content={'- Alpha\n- Beta\n\n1. First\n2. Second'}
      />,
    )

    expect(container.querySelector('ul')).toBeInTheDocument()
    expect(container.querySelector('ol')).toBeInTheDocument()
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()
  })

  it('renders tables with GFM', () => {
    const { container } = render(
      <MarkdownRenderer
        content={'| Name | Role |\n| --- | --- |\n| Ada | Admin |'}
      />,
    )

    const table = container.querySelector('table')
    expect(table).toBeInTheDocument()
    expect(screen.getByText('Ada')).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('renders fenced code blocks', () => {
    const { container } = render(
      <MarkdownRenderer content={'```python\nprint("hello")\n```'} />,
    )

    const codeBlock = container.querySelector('pre code.language-python')
    expect(codeBlock).toBeInTheDocument()
    expect(codeBlock).toHaveTextContent('print("hello")')
  })

  it('renders inline code', () => {
    render(<MarkdownRenderer content={'Use `npm run dev` to start.'} />)

    const inlineCode = screen.getByText('npm run dev')
    expect(inlineCode.tagName).toBe('CODE')
  })

  it('renders safe links in a new tab', () => {
    render(<MarkdownRenderer content={'[Example](https://example.com)'} />)

    const link = screen.getByRole('link', { name: 'Example' })
    expect(link).toHaveAttribute('href', 'https://example.com')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('does not render raw HTML or scripts', () => {
    const { container } = render(
      <MarkdownRenderer
        content={'<script>alert("xss")</script>\n\n<img src=x onerror=alert(1) />'}
      />,
    )

    expect(container.querySelector('script')).not.toBeInTheDocument()
    expect(container.querySelector('img')).not.toBeInTheDocument()
  })

  it('does not render unsafe javascript links', () => {
    render(<MarkdownRenderer content={'[Bad link](javascript:alert(1))'} />)

    expect(screen.queryByRole('link', { name: 'Bad link' })).not.toBeInTheDocument()
    expect(screen.getByText('Bad link')).toBeInTheDocument()
  })
})
