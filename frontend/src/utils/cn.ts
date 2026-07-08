import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge Tailwind CSS class names safely.
 *
 * Combines clsx (conditional classes) with tailwind-merge (deduplication
 * of conflicting Tailwind utilities such as `px-2 px-4` → `px-4`).
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
