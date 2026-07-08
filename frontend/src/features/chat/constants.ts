/**
 * Conversation management constants (Phase 9.2).
 */

/** Matches backend `MAX_TITLE_LENGTH` in conversation_service.py. */
export const MAX_CONVERSATION_TITLE_LENGTH = 500

/** Backend exposes PUT /conversations/{id} for rename (Phase 6.7). */
export const CONVERSATION_RENAME_API_AVAILABLE = true

export const RENAME_UNAVAILABLE_MESSAGE =
  'Conversation rename is not available yet. The backend does not expose PUT /conversations/{id}.'
