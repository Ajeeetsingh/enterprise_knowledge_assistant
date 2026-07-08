/**
 * Design tokens — single source of truth for JS/TS consumers.
 *
 * These mirror the CSS custom properties declared in global.css @theme.
 * Use the Tailwind utility classes in JSX wherever possible; reference
 * these constants only when you need a raw value in JavaScript logic.
 */

export const colors = {
  primary: {
    50:  '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },
  success: { 50: '#f0fdf4', 500: '#22c55e', 700: '#15803d' },
  warning: { 50: '#fffbeb', 500: '#f59e0b', 700: '#b45309' },
  error:   { 50: '#fef2f2', 500: '#ef4444', 700: '#b91c1c' },
  info:    { 50: '#f0f9ff', 500: '#0ea5e9', 700: '#0369a1' },
} as const

export const spacing = {
  0:    '0',
  1:    '0.25rem',
  2:    '0.5rem',
  3:    '0.75rem',
  4:    '1rem',
  6:    '1.5rem',
  8:    '2rem',
  12:   '3rem',
  16:   '4rem',
} as const

export const radius = {
  sm:   '0.25rem',
  md:   '0.375rem',
  lg:   '0.5rem',
  xl:   '0.75rem',
  full: '9999px',
} as const

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
} as const

export const typography = {
  fontFamily: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    mono: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  },
  fontSize: {
    xs:   '0.75rem',
    sm:   '0.875rem',
    base: '1rem',
    lg:   '1.125rem',
    xl:   '1.25rem',
    '2xl':'1.5rem',
    '3xl':'1.875rem',
    '4xl':'2.25rem',
  },
} as const
