import Badge from '@/components/ui/Badge'

export interface UserStatusBadgeProps {
  isActive: boolean
}

export default function UserStatusBadge({ isActive }: UserStatusBadgeProps) {
  if (isActive) {
    return <Badge variant="success">Active</Badge>
  }

  return <Badge variant="error">Inactive</Badge>
}
