import { type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

import { cn } from '@/utils/cn'

export interface AnimatedOutletProps {
  children: ReactNode
  className?: string
}

export default function AnimatedOutlet({ children, className }: AnimatedOutletProps) {
  const location = useLocation()

  return (
    <div
      key={location.pathname}
      className={cn('animate-page-enter', className)}
    >
      {children}
    </div>
  )
}
