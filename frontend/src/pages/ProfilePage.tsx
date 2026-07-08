import { Card } from '@/components/ui'
import Badge from '@/components/ui/Badge'
import { useAuth } from '@/contexts/AuthContext'
import { getUserRoleLabel } from '@/utils/userDisplay'

export default function ProfilePage() {
  const { user } = useAuth()

  if (!user) {
    return null
  }

  const roleLabel = getUserRoleLabel(user.roles, user.is_superuser)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">My Profile</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          View your account details. Profile editing will be available in a future phase.
        </p>
      </div>

      <Card title="Account details">
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Full name
            </dt>
            <dd className="mt-1 text-sm text-neutral-900 dark:text-neutral-50">{user.full_name}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Email
            </dt>
            <dd className="mt-1 text-sm text-neutral-900 dark:text-neutral-50">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Role
            </dt>
            <dd className="mt-1">
              <Badge variant="info">{roleLabel}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
              Status
            </dt>
            <dd className="mt-1">
              <Badge variant={user.is_active ? 'success' : 'error'}>
                {user.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </dd>
          </div>
        </dl>
      </Card>
    </div>
  )
}
