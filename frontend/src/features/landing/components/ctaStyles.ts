import { cn } from '@/utils/cn'

const focusRing =
  'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgb(109_40_217_/_0.25)]'

/** Shared CTA styles for the public landing page only. */
export const ctaPrimaryClass = cn(
  'inline-flex items-center justify-center rounded-xl font-semibold',
  'h-11 px-5 text-sm gap-2 sm:h-12 sm:px-6 sm:text-base',
  'bg-gradient-to-r from-[#3B82F6] to-[#6D28D9] text-white',
  'shadow-[0_10px_28px_-8px_rgba(109,40,217,0.45)]',
  'transition-[transform,box-shadow,filter] duration-200 ease-out',
  'hover:-translate-y-0.5 hover:brightness-105',
  'hover:shadow-[0_14px_36px_-8px_rgba(109,40,217,0.55)]',
  'active:translate-y-0 active:scale-[0.99] active:brightness-95',
  focusRing,
)

export const ctaSecondaryClass = cn(
  'inline-flex items-center justify-center rounded-xl font-semibold',
  'h-11 px-5 text-sm gap-2 sm:h-12 sm:px-6 sm:text-base',
  'border border-white/60 bg-[rgba(255,255,255,0.8)] text-[#1F2937]',
  'shadow-[0_4px_16px_rgba(15,18,34,0.06)]',
  'transition-[transform,background-color,border-color,box-shadow,color] duration-200 ease-out',
  'hover:border-[rgba(109,40,217,0.28)] hover:bg-white hover:text-[#111827]',
  'hover:shadow-[0_8px_22px_rgba(15,18,34,0.08)]',
  'active:scale-[0.99]',
  focusRing,
)

export const ctaNavPrimaryClass = cn(
  'inline-flex items-center justify-center rounded-xl font-semibold',
  'h-8 px-3.5 text-sm gap-1.5',
  'bg-gradient-to-r from-[#3B82F6] to-[#6D28D9] text-white',
  'shadow-[0_8px_20px_-6px_rgba(109,40,217,0.4)]',
  'transition-[transform,box-shadow,filter] duration-200 ease-out',
  'hover:-translate-y-px hover:brightness-105',
  'hover:shadow-[0_10px_26px_-6px_rgba(109,40,217,0.5)]',
  'active:translate-y-0 active:scale-[0.99] active:brightness-95',
  focusRing,
)

export const ctaNavGhostClass = cn(
  'inline-flex items-center justify-center rounded-xl px-3 py-2 text-sm font-medium',
  'border border-transparent bg-[rgba(255,255,255,0.8)] text-[#1F2937]',
  'transition-[background-color,border-color,color,box-shadow] duration-200',
  'hover:border-[rgba(109,40,217,0.22)] hover:bg-white hover:text-[#111827]',
  'hover:shadow-[0_4px_12px_rgba(15,18,34,0.06)]',
  focusRing,
)
