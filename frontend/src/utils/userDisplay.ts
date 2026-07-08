/** Display helpers for authenticated user identity in the UI. */

export function getUserInitials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0]!.charAt(0).toUpperCase()
  return `${parts[0]!.charAt(0)}${parts[parts.length - 1]!.charAt(0)}`.toUpperCase()
}

export function getUserRoleLabel(roles: string[], isSuperuser: boolean): string {
  if (isSuperuser) return 'Superuser'
  if (roles.length === 0) return 'User'
  return roles.join(', ')
}
