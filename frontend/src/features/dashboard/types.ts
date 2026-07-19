/**
 * Personal workspace summary — GET /workspace/summary.
 */

export interface WorkspaceSummary {
  documents_available: number
  conversations: number
  questions_asked: number
  /** Null until a collections API exists. */
  collections: number | null
}
