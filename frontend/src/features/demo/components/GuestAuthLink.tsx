import { Link, useNavigate } from 'react-router-dom'
import type { MouseEvent, ReactNode } from 'react'

import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/utils/cn'

import { GUEST_POST_AUTH_PATH } from '../constants'
import { loadGuestSession } from '../storage/guestSessionStorage'
import { markGuestImportPending } from '../storage/guestTransitionStorage'

export interface GuestAuthLinkProps {
  to?: '/login' | '/register'
  className?: string
  children: ReactNode
  onClick?: (event: MouseEvent<HTMLAnchorElement | HTMLButtonElement>) => void
}

/**
 * Sign In / Create Account control from the guest demo.
 * Preserves a safe return intent without putting conversation contents in the URL.
 * Authenticated visitors are sent to chat (with an explicit continue choice when history exists).
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
          if (loadGuestSession().messages.length > 0) {
            markGuestImportPending()
          }
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
