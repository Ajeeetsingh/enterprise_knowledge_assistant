/** Public guest demo constants. */

export const GUEST_SUGGESTED_QUESTIONS = [
  'What can this assistant help me with?',
  'How does Knowra work?',
  'How are answers sourced?',
  'What document formats are supported?',
] as const

export const GUEST_CONVERSATION_ID = 'guest-demo'

/** Max successfully processed user questions per browser session. */
export const GUEST_QUESTION_LIMIT = 10

/** sessionStorage key (versioned). */
export const GUEST_STORAGE_KEY = 'eka.guest-demo.v1'

/**
 * Lightweight flag: user left /demo intending to continue after auth.
 * Does not store conversation contents (those remain under GUEST_STORAGE_KEY).
 */
export const GUEST_TRANSITION_KEY = 'eka.guest-transition.v1'

/** Cap persisted messages (user + assistant). */
export const GUEST_STORAGE_MAX_MESSAGES = 24

/** History sent to the API (must stay within backend limits). */
export const GUEST_API_HISTORY_MAX_MESSAGES = 6

/** Post-auth redirect target when a guest import choice is pending. */
export const GUEST_POST_AUTH_PATH = '/chat'
