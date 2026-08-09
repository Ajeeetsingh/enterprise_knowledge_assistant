import { Link, useNavigate } from 'react-router-dom'
import type { MouseEvent, ReactNode } from 'react'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import { GUEST_POST_AUTH_PATH } from '../constants'
import {
  clearAllGuestDemoState,
  markGuestImportPending,
} from '../storage/guestTransitionStorage'

export interface GuestAuthLinkProps {
  to?: '/login' | '/register'
  className?: string
  children: ReactNode
  onClick?: (event: MouseEvent<HTMLAnchorElement | HTMLButtonElement>) => void
}

/**
 * Sign In / Create Account control from the guest demo.
 * Preserves a safe return intent without putting conversation contents in the URL.
 *
 * Already-authenticated visitors go straight to the workspace — never show the
 * guest migration banner (auth takes precedence over leftover demo state).
 */
export default function GuestAuthLink({
  to = '/login',
  className,
  children,
  onClick,
}: GuestAuthLinkProps) {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  if (isAuthenticated) {
    return (
      <button
        type="button"
        className={className}
        onClick={(event) => {
          onClick?.(event)
          clearAllGuestDemoState()
          navigate(GUEST_POST_AUTH_PATH)
        }}
      >
        {children}
      </button>
    )
  }

  return (
    <Link
      to={to}
      state={{ from: GUEST_POST_AUTH_PATH }}
      className={cn(className)}
      onClick={(event) => {
        markGuestImportPending()
        onClick?.(event)
      }}
    >
      {children}
    </Link>
  )
}
