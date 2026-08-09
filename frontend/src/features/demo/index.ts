export { default as GuestDemoPage } from './pages/GuestDemoPage'
export {
  GUEST_SUGGESTED_QUESTIONS,
  GUEST_QUESTION_LIMIT,
  GUEST_POST_AUTH_PATH,
  GUEST_STORAGE_KEY,
  GUEST_TRANSITION_KEY,
  GUEST_CONTINUE_READY_KEY,
} from './constants'
export {
  loadGuestSession,
  saveGuestSession,
  clearGuestSession,
} from './storage/guestSessionStorage'
export {
  markGuestImportPending,
  clearGuestImportPending,
  clearAllGuestDemoState,
  isGuestImportPending,
  shouldOfferGuestContinue,
  armGuestContinuePrompt,
  consumeGuestContinuePrompt,
  shouldPreserveGuestContinueOnAuth,
} from './storage/guestTransitionStorage'
export { default as GuestContinuePrompt } from './components/GuestContinuePrompt'
export { default as GuestAuthLink } from './components/GuestAuthLink'
