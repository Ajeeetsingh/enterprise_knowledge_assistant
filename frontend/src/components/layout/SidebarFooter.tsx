import { cn } from '@/utils/cn'

export interface SidebarFooterProps {
  collapsed?: boolean
  className?: string
}

export default function SidebarFooter({ collapsed = false, className }: SidebarFooterProps) {
  return (
    <div className={cn('sidebar-footer', className)}>
      <span className="flex items-center gap-2">
        <span
          className="inline-flex size-1.5 shrink-0 rounded-full bg-success-500"
          aria-hidden
        />
        <span>{collapsed ? 'v1' : 'v1.0.0'}</span>
      </span>

      {!collapsed && <span className="status-pill">Operational</span>}
    </div>
  )
}
