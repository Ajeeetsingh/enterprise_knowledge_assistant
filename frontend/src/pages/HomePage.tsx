import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-12 text-center">
      <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">
        Enterprise Knowledge Assistant
      </h1>
      <p className="mt-2 text-neutral-500 dark:text-neutral-400">
        Your organisation&apos;s AI-powered knowledge platform.
      </p>
      <nav className="mt-8 flex flex-wrap justify-center gap-4 text-sm">
        <Link to="/login" className="text-primary-600 hover:underline dark:text-primary-400">
          Sign in
        </Link>
        <Link to="/dashboard" className="text-primary-600 hover:underline dark:text-primary-400">
          Dashboard
        </Link>
        <Link
          to="/layout-preview"
          className="text-primary-600 hover:underline dark:text-primary-400"
        >
          Layout preview
        </Link>
        <Link
          to="/auth-debug"
          className="text-primary-600 hover:underline dark:text-primary-400"
        >
          Auth debug
        </Link>
        <Link
          to="/design-system"
          className="text-primary-600 hover:underline dark:text-primary-400"
        >
          Design system
        </Link>
      </nav>
    </main>
  )
}
