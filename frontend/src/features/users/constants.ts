/** Email validation pattern for create-user form. */
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Backend exposes PUT /users/{id} for profile updates but user editing is out of
 * scope for Phase 9.4A. Disable uses DELETE /users/{id} (soft-delete).
 */
export const USER_EDIT_API_NOTE =
  'User profile editing (PUT /users/{id}) is available on the backend but not implemented in this phase.'
