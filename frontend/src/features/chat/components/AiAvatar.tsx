import { cn } from '@/utils/cn'

export interface AiAvatarProps {
  className?: string
}

export default function AiAvatar({ className }: AiAvatarProps) {
  return (
    <span
      aria-hidden
      className={cn(
        'mt-1 inline-flex size-7 shrink-0 rounded-full bg-gradient-accent shadow-accent-glow',
        className,
      )}
    />
  )
}
