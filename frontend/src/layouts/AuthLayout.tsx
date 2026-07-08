import { Outlet } from 'react-router-dom'

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-neutral-50 px-4 py-12 dark:bg-neutral-950 sm:px-6">
      <div className="mb-8 text-center">
        <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Enterprise Knowledge Assistant
        </p>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Sign in to your account
        </p>
      </div>

      <div className="w-full max-w-md">
        <Outlet />
      </div>
    </div>
  )
}
