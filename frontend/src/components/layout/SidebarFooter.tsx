import { cn } from '@/utils/cn'

export interface SidebarFooterProps {
  collapsed?: boolean
  className?: string
}

export default function SidebarFooter({ collapsed = false, className }: SidebarFooterProps) {
  return (
    <div className={cn('sidebar-footer', className)}>
      <span className="sidebar-footer__version">
        <span className="sidebar-footer__dot" aria-hidden />
        <span>{collapsed ? 'v1' : 'v1.0.0'}</span>
      </span>

      {!collapsed && <span className="sidebar-footer__status">Operational</span>}
    </div>
  )
}
