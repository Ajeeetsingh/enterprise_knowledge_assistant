import type { ExportConversationModel } from './buildExportModel'
import type { ExportOptions } from './types'

/**
 * JSON export always preserves the full conversation structure — per spec,
 * it's meant for programmatic reuse, so it isn't filtered by the include
 * toggles the way Markdown/PDF/Text are. The requested options are still
 * recorded (as `exportedWithOptions`) so downstream tooling knows what the
 * user asked for when they triggered the export.
 */
export function generateJson(model: ExportConversationModel, options: ExportOptions): string {
  const payload = {
    ...model,
    exportedWithOptions: options,
  }
  return JSON.stringify(payload, null, 2) + '\n'
}
