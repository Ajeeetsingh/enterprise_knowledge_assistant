import { Link, Outlet, useLocation } from 'react-router-dom'

import { cn } from '@/utils/cn'

export default function AuthLayout() {
  const location = useLocation()
  const isRegister = location.pathname.startsWith('/register')

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-12 sm:px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-[42%] h-[28rem] w-[28rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,var(--accent-muted)_0%,transparent_68%)] blur-3xl"
      />

      <div className="relative z-10 mb-8 flex flex-col items-center text-center">
        <Link
          to="/"
          className={cn(
            'mb-4 inline-flex rounded-md',
            'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
          )}
        >
          <img
            src="/favicon.svg"
            alt=""
            width={36}
            height={34}
            className="size-9"
          />
          <span className="sr-only">Knowra home</span>
        </Link>

        <h1 className="font-display text-lg font-semibold tracking-tight text-foreground sm:text-xl">
          Knowra
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          {isRegister ? 'Create your account' : 'Sign in to your account'}
        </p>
      </div>

      <div className="relative z-10 w-full max-w-md">
        <Outlet />
      </div>
    </div>
  )
}
