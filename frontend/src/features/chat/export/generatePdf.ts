import { jsPDF } from 'jspdf'

import type { ExportConversationModel, ExportMessageModel } from './buildExportModel'
import { formatConfidencePercent, formatExportDateTime } from './formatters'
import type { ExportOptions } from './types'

const APP_NAME = 'Enterprise Knowledge Assistant'

interface PdfPalette {
  background: string
  surfaceBand: string
  textPrimary: string
  textSecondary: string
  textTertiary: string
  accent: string
  accentContrast: string
  divider: string
}

/** Mirrors `global.css`'s `[data-theme="dark"]` tokens. */
const DARK_PALETTE: PdfPalette = {
  background: '#0a0a0b',
  surfaceBand: '#131417',
  textPrimary: '#f5f5f7',
  textSecondary: '#9a9aa2',
  textTertiary: '#5c5c64',
  accent: '#8b6eff',
  accentContrast: '#ffffff',
  divider: '#2a2a2e',
}

/** Mirrors `global.css`'s `[data-theme="light"]` tokens. */
const LIGHT_PALETTE: PdfPalette = {
  background: '#ffffff',
  surfaceBand: '#fafafa',
  textPrimary: '#1a1a1e',
  textSecondary: '#6b6b75',
  textTertiary: '#a0a0a8',
  accent: '#6b46e5',
  accentContrast: '#ffffff',
  divider: '#e2e2e5',
}

const PAGE_MARGIN = 56
const HEADER_BAND_HEIGHT = 46
const FOOTER_HEIGHT = 40
const BODY_FONT_SIZE = 10.5
const BODY_LINE_HEIGHT = 15

/** Minimal imperative helper for laying out flowing, page-break-aware PDF content. */
class PdfWriter {
  readonly doc: jsPDF
  readonly palette: PdfPalette
  readonly model: ExportConversationModel
  readonly pageWidth: number
  readonly pageHeight: number
  readonly contentLeft: number
  readonly contentWidth: number
  readonly contentBottom: number
  y = 0
  private pageCount = 0

  constructor(doc: jsPDF, palette: PdfPalette, model: ExportConversationModel) {
    this.doc = doc
    this.palette = palette
    this.model = model
    this.pageWidth = doc.internal.pageSize.getWidth()
    this.pageHeight = doc.internal.pageSize.getHeight()
    this.contentLeft = PAGE_MARGIN
    this.contentWidth = this.pageWidth - PAGE_MARGIN * 2
    this.contentBottom = this.pageHeight - FOOTER_HEIGHT
  }

  private paintBackground() {
    this.doc.setFillColor(this.palette.background)
    this.doc.rect(0, 0, this.pageWidth, this.pageHeight, 'F')
  }

  private drawHeaderBand(isFirstPage: boolean) {
    const { doc, palette, model } = this
    doc.setFillColor(palette.surfaceBand)
    doc.rect(0, 0, this.pageWidth, HEADER_BAND_HEIGHT, 'F')
    doc.setDrawColor(palette.divider)
    doc.setLineWidth(0.75)
    doc.line(0, HEADER_BAND_HEIGHT, this.pageWidth, HEADER_BAND_HEIGHT)

    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.setTextColor(palette.accent)
    doc.text(APP_NAME, this.contentLeft, HEADER_BAND_HEIGHT / 2 - 2)

    doc.setFont('helvetica', 'normal')
    doc.setFontSize(9)
    doc.setTextColor(palette.textSecondary)
    const titleLabel = isFirstPage ? 'Conversation Export' : model.title
    doc.text(titleLabel, this.contentLeft, HEADER_BAND_HEIGHT / 2 + 12, { maxWidth: this.contentWidth })
  }

  startPage(isFirstPage: boolean) {
    if (!isFirstPage) this.doc.addPage()
    this.pageCount += 1
    this.paintBackground()
    this.drawHeaderBand(isFirstPage)
    this.y = HEADER_BAND_HEIGHT + 28
  }

  /** Adds a new page (with header/background) if `height` won't fit before the footer line. */
  ensureSpace(height: number) {
    if (this.y + height > this.contentBottom) {
      this.startPage(false)
    }
  }

  addGap(height: number) {
    this.y += height
  }

  setTextStyle(style: 'normal' | 'bold' | 'italic' = 'normal', size = BODY_FONT_SIZE, color = this.palette.textPrimary) {
    this.doc.setFont('helvetica', style)
    this.doc.setFontSize(size)
    this.doc.setTextColor(color)
  }

  /** Renders wrapped paragraph text, breaking across pages line-by-line as needed. */
  writeParagraph(
    text: string,
    options: {
      style?: 'normal' | 'bold' | 'italic'
      size?: number
      color?: string
      lineHeight?: number
      indent?: number
    } = {},
  ) {
    const {
      style = 'normal',
      size = BODY_FONT_SIZE,
      color = this.palette.textPrimary,
      lineHeight = BODY_LINE_HEIGHT,
      indent = 0,
    } = options
    this.setTextStyle(style, size, color)
    const maxWidth = this.contentWidth - indent
    const lines: string[] = this.doc.splitTextToSize(text, maxWidth)
    lines.forEach((line) => {
      this.ensureSpace(lineHeight)
      this.doc.text(line, this.contentLeft + indent, this.y)
      this.y += lineHeight
    })
  }

  drawDivider() {
    this.ensureSpace(16)
    this.y += 6
    this.doc.setDrawColor(this.palette.divider)
    this.doc.setLineWidth(0.75)
    this.doc.line(this.contentLeft, this.y, this.contentLeft + this.contentWidth, this.y)
    this.y += 16
  }

  finalizeFooters() {
    const total = this.doc.getNumberOfPages()
    for (let page = 1; page <= total; page += 1) {
      this.doc.setPage(page)
      this.doc.setDrawColor(this.palette.divider)
      this.doc.setLineWidth(0.75)
      this.doc.line(
        this.contentLeft,
        this.pageHeight - FOOTER_HEIGHT + 10,
        this.contentLeft + this.contentWidth,
        this.pageHeight - FOOTER_HEIGHT + 10,
      )
      this.doc.setFont('helvetica', 'normal')
      this.doc.setFontSize(8.5)
      this.doc.setTextColor(this.palette.textTertiary)
      this.doc.text(`${APP_NAME} · Confidential`, this.contentLeft, this.pageHeight - FOOTER_HEIGHT + 24)
      this.doc.text(
        `Page ${page} of ${total}`,
        this.contentLeft + this.contentWidth,
        this.pageHeight - FOOTER_HEIGHT + 24,
        { align: 'right' },
      )
    }
  }
}

function roleLabel(role: ExportMessageModel['role']): string {
  if (role === 'user') return 'You'
  if (role === 'assistant') return 'Assistant'
  return 'System'
}

function writeTitleBlock(writer: PdfWriter, model: ExportConversationModel, options: ExportOptions) {
  writer.setTextStyle('bold', 20, writer.palette.textPrimary)
  writer.doc.text(model.title, writer.contentLeft, writer.y)
  writer.y += 26

  writer.setTextStyle('normal', 10, writer.palette.textSecondary)
  writer.doc.text(`Exported ${formatExportDateTime(model.exportedAtIso)}`, writer.contentLeft, writer.y)
  writer.y += 14

  if (options.includeTimestamps) {
    writer.doc.text(
      `Conversation started ${formatExportDateTime(model.createdAtIso)}`,
      writer.contentLeft,
      writer.y,
    )
    writer.y += 14
  }
  writer.y += 6
  writer.drawDivider()
}

function writeDocumentNames(writer: PdfWriter, model: ExportConversationModel) {
  if (model.documentNames.length === 0) return
  writer.writeParagraph('Documents Referenced', { style: 'bold', size: 11.5 })
  writer.addGap(2)
  model.documentNames.forEach((name) => {
    writer.writeParagraph(`•  ${name}`, { color: writer.palette.textSecondary, indent: 4 })
  })
  writer.drawDivider()
}

function writeCitations(writer: PdfWriter, message: ExportMessageModel, options: ExportOptions) {
  if (!options.includeSources || message.citations.length === 0) return

  writer.addGap(2)
  writer.writeParagraph('Sources', { style: 'bold', size: 10, color: writer.palette.textSecondary })
  message.citations.forEach((citation, index) => {
    const pageLabel = citation.page != null ? `, p. ${citation.page}` : ''
    const confidenceLabel = options.includeConfidence
      ? ` (${formatConfidencePercent(citation.confidence)} confidence)`
      : ''
    writer.writeParagraph(`${index + 1}. ${citation.source}${pageLabel}${confidenceLabel}`, {
      style: 'bold',
      size: 9.5,
      indent: 4,
    })
    if (citation.excerpt.trim()) {
      writer.writeParagraph(`"${citation.excerpt.trim().replace(/\s+/g, ' ')}"`, {
        style: 'italic',
        size: 9,
        color: writer.palette.textSecondary,
        indent: 10,
      })
    }
  })
}

function writeMessage(writer: PdfWriter, message: ExportMessageModel, options: ExportOptions) {
  const isAssistant = message.role === 'assistant'
  writer.ensureSpace(BODY_LINE_HEIGHT * 2)

  writer.setTextStyle('bold', 11, isAssistant ? writer.palette.accent : writer.palette.textPrimary)
  writer.doc.text(roleLabel(message.role), writer.contentLeft, writer.y)

  if (options.includeTimestamps) {
    writer.setTextStyle('normal', 9, writer.palette.textTertiary)
    writer.doc.text(formatExportDateTime(message.createdAtIso), writer.contentLeft + writer.contentWidth, writer.y, {
      align: 'right',
    })
  }
  writer.y += 16

  writer.writeParagraph(message.content.trim())

  if (isAssistant && options.includeConfidence && message.confidenceScore != null) {
    writer.addGap(2)
    writer.writeParagraph(`Confidence: ${formatConfidencePercent(message.confidenceScore)}`, {
      style: 'bold',
      size: 9.5,
      color: writer.palette.textSecondary,
    })
  }

  writeCitations(writer, message, options)
  writer.drawDivider()
}

export function generatePdfBlob(
  model: ExportConversationModel,
  options: ExportOptions,
  theme: 'light' | 'dark',
): Blob {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const palette = theme === 'dark' ? DARK_PALETTE : LIGHT_PALETTE
  const writer = new PdfWriter(doc, palette, model)

  writer.startPage(true)
  writeTitleBlock(writer, model, options)

  if (options.includeDocumentNames) {
    writeDocumentNames(writer, model)
  }

  model.messages.forEach((message) => writeMessage(writer, message, options))

  writer.finalizeFooters()

  return doc.output('blob')
}
