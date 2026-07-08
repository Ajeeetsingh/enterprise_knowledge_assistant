import { Card } from '@/components/ui'
import { MAIN_NAV_ITEMS } from '@/components/layout'

export default function LayoutPreviewPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
          Layout Preview
        </h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Visual verification of AppLayout, Sidebar, TopNavbar, and PageContainer.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="AppLayout">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Shell layout combining Sidebar, TopNavbar, and PageContainer. Used for
            authenticated application pages such as Dashboard.
          </p>
        </Card>

        <Card title="Sidebar">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Collapsible navigation on desktop (toggle « / »). Hidden on mobile until
            the Menu button is pressed. Supports collapsed and expanded states.
          </p>
          <ul className="mt-3 space-y-1 text-sm text-neutral-700 dark:text-neutral-300">
            {MAIN_NAV_ITEMS.map((item) => (
              <li key={item.path}>
                {item.label} — <code className="text-xs">{item.path}</code>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="TopNavbar">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Application title, theme toggle, and an interactive user menu with profile
            and logout actions. Includes mobile menu and desktop sidebar controls.
          </p>
        </Card>

        <Card title="PageContainer">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Provides consistent responsive padding and a max-width of{' '}
            <code className="text-xs">7xl</code> for page content.
          </p>
        </Card>
      </div>

      <Card title="Responsive behaviour">
        <ul className="list-inside list-disc space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
          <li>
            <strong>Desktop (lg+):</strong> Sidebar always visible; collapse toggle
            narrows it to icon-only labels.
          </li>
          <li>
            <strong>Tablet / mobile:</strong> Sidebar hidden off-screen; Menu button
            opens it as an overlay drawer.
          </li>
          <li>
            <strong>Auth pages:</strong> AuthLayout centres content for /login and
            future /auth/* routes.
          </li>
        </ul>
      </Card>
    </div>
  )
}
