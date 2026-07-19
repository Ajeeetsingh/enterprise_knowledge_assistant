import { type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react'

import { cn } from '@/utils/cn'

export interface FilterLabelProps {
  htmlFor: string
  children: ReactNode
  className?: string
}

export function FilterLabel({ htmlFor, children, className }: FilterLabelProps) {
  return (
    <label htmlFor={htmlFor} className={cn('filter-label', className)}>
      {children}
    </label>
  )
}

function SearchIcon() {
  return (
    <svg
      aria-hidden
      className="filter-search-icon size-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <circle cx="11" cy="11" r="7" />
      <path strokeLinecap="round" d="M20 20l-3-3" />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden
      className="filter-select-chevron size-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 9l6 6 6-6" />
    </svg>
  )
}

export interface FilterSearchProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
}

export function FilterSearch({ label, id, className, ...props }: FilterSearchProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, '-')

  return (
    <div>
      <FilterLabel htmlFor={inputId}>{label}</FilterLabel>
      <div className="filter-search-wrap">
        <SearchIcon />
        <input id={inputId} className={cn('filter-control', className)} {...props} />
      </div>
    </div>
  )
}

export interface FilterSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  options: ReadonlyArray<{ value: string; label: string }>
}

export function FilterSelect({ label, id, options, className, ...props }: FilterSelectProps) {
  const selectId = id ?? label.toLowerCase().replace(/\s+/g, '-')

  return (
    <div>
      <FilterLabel htmlFor={selectId}>{label}</FilterLabel>
      <div className="filter-select-wrap">
        <select id={selectId} className={cn('filter-control', className)} {...props}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronIcon />
      </div>
    </div>
  )
}

export interface FilterBarProps {
  children: ReactNode
  className?: string
  'aria-label'?: string
}

export function FilterBar({ children, className, 'aria-label': ariaLabel }: FilterBarProps) {
  return (
    <section
      aria-label={ariaLabel}
      className={cn(
        'flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-raised p-4 shadow-elevation-sm sm:flex-row sm:flex-wrap sm:items-end',
        className,
      )}
    >
      {children}
    </section>
  )
}
