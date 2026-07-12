import { useCallback, useState } from 'react'

export function useLocalStorageState<T>(
  key: string,
  initialValue: T,
  serialize: (value: T) => string = String,
  deserialize: (value: string) => T = (value) => value as T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue
    const raw = localStorage.getItem(key)
    if (raw === null) return initialValue
    try {
      return deserialize(raw)
    } catch {
      return initialValue
    }
  })

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const next = typeof value === 'function' ? (value as (prev: T) => T)(prev) : value
        localStorage.setItem(key, serialize(next))
        return next
      })
    },
    [key, serialize],
  )

  return [storedValue, setValue]
}
