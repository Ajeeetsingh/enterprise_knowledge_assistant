import { useTheme } from '@/contexts/ThemeContext'
import { Badge, Button, Card, EmptyState, Input, Spinner } from '@/components/ui'
import { useState } from 'react'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-50 border-b border-neutral-200 dark:border-neutral-700 pb-2">
        {title}
      </h2>
      {children}
    </section>
  )
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap items-center gap-3">{children}</div>
}

export default function DesignSystemPage() {
  const { theme, toggleTheme } = useTheme()
  const [inputValue, setInputValue] = useState('')

  return (
    <main className="min-h-screen bg-neutral-50 dark:bg-neutral-950 py-12">
      <div className="mx-auto max-w-4xl px-6 flex flex-col gap-12">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">
              Design System
            </h1>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              Knowra — UI component showcase
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={toggleTheme}>
            {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
          </Button>
        </div>

        {/* Buttons */}
        <Section title="Button">
          <div className="flex flex-col gap-3">
            <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Variants</p>
            <Row>
              <Button variant="primary">Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="danger">Danger</Button>
              <Button variant="ghost">Ghost</Button>
            </Row>

            <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Sizes</p>
            <Row>
              <Button size="sm">Small</Button>
              <Button size="md">Medium</Button>
              <Button size="lg">Large</Button>
            </Row>

            <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">States</p>
            <Row>
              <Button isLoading>Loading</Button>
              <Button disabled>Disabled</Button>
            </Row>
          </div>
        </Section>

        {/* Input */}
        <Section title="Input">
          <div className="flex flex-col gap-4 max-w-sm">
            <Input
              label="Email address"
              placeholder="you@example.com"
              type="email"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              hint="We will never share your email."
            />
            <Input
              label="Password"
              placeholder="••••••••"
              type="password"
              error="Password must be at least 8 characters."
            />
            <Input
              label="Disabled field"
              placeholder="Cannot edit"
              disabled
            />
          </div>
        </Section>

        {/* Card */}
        <Section title="Card">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card title="Simple card">
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                This is the card body. Cards surface information in a contained, elevated panel.
              </p>
            </Card>

            <Card
              title="Card with footer"
              footer={
                <div className="flex justify-end gap-2">
                  <Button variant="secondary" size="sm">Cancel</Button>
                  <Button size="sm">Save</Button>
                </div>
              }
            >
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Cards can include an optional footer for actions or metadata.
              </p>
            </Card>
          </div>
        </Section>

        {/* Spinner */}
        <Section title="Spinner">
          <Row>
            <Spinner size="sm" />
            <Spinner size="md" />
            <Spinner size="lg" />
          </Row>
        </Section>

        {/* Badge */}
        <Section title="Badge">
          <Row>
            <Badge variant="success">Success</Badge>
            <Badge variant="warning">Warning</Badge>
            <Badge variant="error">Error</Badge>
            <Badge variant="info">Info</Badge>
          </Row>
        </Section>

        {/* Empty State */}
        <Section title="Empty State">
          <Card>
            <EmptyState
              icon={
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="size-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                </svg>
              }
              title="No documents yet"
              description="Upload your first document to get started."
              action={<Button size="sm">Upload document</Button>}
            />
          </Card>
        </Section>

        {/* Color palette */}
        <Section title="Color Palette">
          <div className="flex flex-col gap-2">
            {(['primary', 'success', 'warning', 'error', 'info'] as const).map((name) => (
              <div key={name} className="flex items-center gap-2">
                <span className="w-20 text-xs font-medium capitalize text-neutral-500 dark:text-neutral-400">{name}</span>
                <div className="flex gap-1">
                  {([50, 500, 700] as const).map((shade) => (
                    <div
                      key={shade}
                      title={`${name}-${shade}`}
                      className={`size-8 rounded-md bg-${name}-${shade}`}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>

      </div>
    </main>
  )
}
