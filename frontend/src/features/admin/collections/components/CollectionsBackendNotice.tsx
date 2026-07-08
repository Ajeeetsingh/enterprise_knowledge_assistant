import { COLLECTIONS_BACKEND_NOTICE } from '../constants'

export default function CollectionsBackendNotice() {
  return (
    <div
      role="status"
      className="rounded-lg border border-warning-500/30 bg-warning-50 px-4 py-3 text-sm text-warning-800 dark:border-warning-500/20 dark:bg-warning-700/10 dark:text-warning-400"
    >
      {COLLECTIONS_BACKEND_NOTICE}
    </div>
  )
}
