import { useLocalStorageState } from '@/hooks/useLocalStorageState'

import { DEFAULT_EXPORT_OPTIONS, type ExportOptions } from './types'

const STORAGE_KEY = 'eka-chat-export-options'

function serialize(value: ExportOptions): string {
  return JSON.stringify(value)
}

function deserialize(raw: string): ExportOptions {
  const parsed = JSON.parse(raw) as Partial<ExportOptions>
  return { ...DEFAULT_EXPORT_OPTIONS, ...parsed }
}

/**
 * Persists the user's export option toggles (Include Sources/Confidence/
 * Timestamps/Document Names) across sessions so they don't have to
 * re-select them on every export.
 */
export function useExportPreferences() {
  const [options, setOptions] = useLocalStorageState<ExportOptions>(
    STORAGE_KEY,
    DEFAULT_EXPORT_OPTIONS,
    serialize,
    deserialize,
  )

  function toggleOption(key: keyof ExportOptions) {
    setOptions((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return { options, setOptions, toggleOption }
}
