import { useEffect, useId, useState } from 'react'

import { cn } from '@/utils/cn'

import AuroraKnowledgeFlow, { AuroraWaveLayer } from './AuroraKnowledgeFlow'

const DOCUMENTS = [
  { name: 'HR Policy', format: 'PDF', tone: 'pdf' as const },
  { name: 'Remote Work Policy', format: 'DOCX', tone: 'docx' as const },
  { name: 'Employee Handbook', format: 'DOCX', tone: 'docx' as const },
] as const

const ANSWER_TEXT =
  'Employees may work remotely according to the approved hybrid-work guidelines.'

const SOURCES = [
  { index: 1, label: 'HR Policy' },
  { index: 2, label: 'Handbook' },
] as const

/**
 * Decorative hero composition: documents → aurora knowledge flow → grounded answer.
 * Motion is CSS/SVG-driven (no per-frame React state). Illustrative UI only.
 */
export default function HeroKnowledgeAnimation() {
  const uid = useId().replace(/:/g, '')
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(media.matches)
    const onChange = () => setReducedMotion(media.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  return (
    <div
      className={cn(
        'hero-knowledge-anim pointer-events-none absolute inset-0 overflow-hidden',
        reducedMotion ? 'hero-knowledge-anim--static' : 'hero-knowledge-anim--live',
      )}
      aria-hidden="true"
    >
      {/* Full-bleed wave mesh — outside max-width stage, edge-to-edge */}
      <AuroraWaveLayer uid={uid} />

      <div className="hero-flow-stage">
        <AuroraKnowledgeFlow uid={uid} reducedMotion={reducedMotion} />

        <ul className="hero-flow-docs hero-flow-parallax-docs">
          {DOCUMENTS.map((doc, index) => (
            <li
              key={doc.name}
              className={cn(
                'hero-flow-doc',
                `hero-flow-doc--${index + 1}`,
                index > 0 && 'hero-flow-doc--hide-mobile',
                !reducedMotion && 'hero-flow-doc--animate',
              )}
            >
              <span
                className={cn(
                  'hero-flow-doc-icon',
                  doc.tone === 'pdf' ? 'hero-flow-doc-icon--pdf' : 'hero-flow-doc-icon--docx',
                )}
              >
                {doc.tone === 'pdf' ? <PdfGlyph /> : <DocxGlyph />}
              </span>
              <span className="hero-flow-doc-meta">
                <span className="hero-flow-doc-name">{doc.name}</span>
                <span className="hero-flow-doc-format">{doc.format}</span>
              </span>
            </li>
          ))}
        </ul>

        <div className="hero-flow-parallax-answer">
          <article
            className={cn(
              'hero-flow-answer',
              !reducedMotion && 'hero-flow-answer--animate',
            )}
          >
            <header className="hero-flow-answer-header">
              <span className="hero-flow-answer-mark" aria-hidden>
                ✦
              </span>
              <span>Answer</span>
            </header>
            <p className="hero-flow-answer-body">{ANSWER_TEXT}</p>
            <div className="hero-flow-sources">
              <span className="hero-flow-sources-label">Sources</span>
              <ul>
                {SOURCES.map((source) => (
                  <li key={source.index}>
                    [{source.index}] {source.label}
                  </li>
                ))}
              </ul>
            </div>
          </article>
        </div>
      </div>
    </div>
  )
}

/** Stylized PDF file glyph — distinct from DOCX */
function PdfGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className="hero-flow-doc-glyph">
      <path
        d="M6.75 3.5h6.8L17.25 7.2V19.5a1 1 0 0 1-1 1H6.75a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M13.55 3.5V7.35h3.7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <rect x="7.6" y="12.1" width="8.8" height="4.8" rx="1" fill="currentColor" opacity="0.12" />
      <text
        x="12"
        y="15.55"
        textAnchor="middle"
        fill="currentColor"
        fontSize="3.6"
        fontWeight="700"
        fontFamily="Plus Jakarta Sans, Inter, system-ui, sans-serif"
        letterSpacing="0.04em"
      >
        PDF
      </text>
    </svg>
  )
}

/** Stylized Word/DOCX glyph — visibly different from PDF */
function DocxGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className="hero-flow-doc-glyph">
      <path
        d="M6.75 3.5h6.8L17.25 7.2V19.5a1 1 0 0 1-1 1H6.75a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M13.55 3.5V7.35h3.7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Word-style "W" mark */}
      <path
        d="M8.2 11.1 9.55 17h1.05l.85-3.7.85 3.7H13.35L14.7 11.1h-1.1l-.85 3.55-.8-3.55h-1.1l-.8 3.55-.85-3.55H8.2Z"
        fill="currentColor"
      />
    </svg>
  )
}
