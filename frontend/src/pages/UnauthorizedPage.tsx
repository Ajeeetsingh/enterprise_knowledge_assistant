import { Link } from 'react-router-dom'

import { Card } from '@/components/ui'

export default function UnauthorizedPage() {
  return (
    <div className="flex flex-col items-center gap-6 py-12 text-center">
      <Card className="max-w-lg">
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
          Access Denied
        </h1>
        <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">
          You do not have permission to view this page. Contact your administrator if
          you believe this is an error.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            to="/dashboard"
            className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
          >
            Go to dashboard
          </Link>
          <Link
            to="/"
            className="text-sm font-medium text-neutral-600 hover:underline dark:text-neutral-400"
          >
            Return home
          </Link>
        </div>
      </Card>
    </div>
  )
}
