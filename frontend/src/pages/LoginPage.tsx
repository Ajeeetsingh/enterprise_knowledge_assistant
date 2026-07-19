import { type FormEvent, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { Badge, Button, Card, Input } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'
import type { ApiError } from '@/types'
import { toApiError } from '@/utils/apiError'

interface LoginLocationState {
  from?: string
  registrationSuccess?: string
}

interface FieldErrors {
  email?: string
  password?: string
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    'status' in error &&
    typeof (error as ApiError).message === 'string' &&
    typeof (error as ApiError).status === 'number'
  )
}

function resolveLoginErrorMessage(error: unknown): string {
  const apiError = isApiError(error) ? error : toApiError(error)

  if (apiError.status === 401 || apiError.status === 403) {
    return 'Invalid email or password.'
  }

  if (apiError.status === 0) {
    return apiError.message || 'Network error — please check your connection.'
  }

  return apiError.message || 'An unexpected error occurred. Please try again.'
}

function validateFields(email: string, password: string): FieldErrors {
  const errors: FieldErrors = {}
  const trimmedEmail = email.trim()

  if (!trimmedEmail) {
    errors.email = 'Email is required.'
  } else if (!EMAIL_PATTERN.test(trimmedEmail)) {
    errors.email = 'Enter a valid email address.'
  }

  if (!password) {
    errors.password = 'Password is required.'
  }

  return errors
}

function resolveRedirectPath(from: string | undefined): string {
  if (!from || from === '/login') {
    return '/dashboard'
  }
  return from
}

const showTestUsers = import.meta.env.VITE_SHOW_TEST_USERS === 'true'
const testUserLabel = import.meta.env.VITE_TEST_USER_LABEL as string | undefined
const testUserEmail = import.meta.env.VITE_TEST_USER_EMAIL as string | undefined

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const locationState = location.state as LoginLocationState | null

  const redirectPath = resolveRedirectPath(locationState?.from)
  const registrationSuccess = locationState?.registrationSuccess

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitError(null)

    const errors = validateFields(email, password)
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    setFieldErrors({})
    setIsSubmitting(true)

    try {
      await login({ email: email.trim(), password })
      navigate(redirectPath, { replace: true })
    } catch (error) {
      setSubmitError(resolveLoginErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card title="Sign In">
        {registrationSuccess && (
          <div
            role="status"
            className="mb-4 rounded-[var(--radius-sm)] border border-[color-mix(in_srgb,var(--status-good)_35%,transparent)] bg-[var(--status-good-muted)] px-3 py-2 text-sm text-status-good"
          >
            {registrationSuccess}
          </div>
        )}
        <form className="flex flex-col gap-5" onSubmit={(event) => void handleSubmit(event)} noValidate>
          <Input
            label="Email address"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            disabled={isSubmitting}
            onChange={(event) => {
              setEmail(event.target.value)
              if (fieldErrors.email) {
                setFieldErrors((prev) => {
                  const next = { ...prev }
                  delete next.email
                  return next
                })
              }
            }}
            {...(fieldErrors.email ? { error: fieldErrors.email } : {})}
          />

          <Input
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            disabled={isSubmitting}
            onChange={(event) => {
              setPassword(event.target.value)
              if (fieldErrors.password) {
                setFieldErrors((prev) => {
                  const next = { ...prev }
                  delete next.password
                  return next
                })
              }
            }}
            {...(fieldErrors.password ? { error: fieldErrors.password } : {})}
          />

          {submitError && (
            <div
              role="alert"
              className="rounded-[var(--radius-sm)] border border-[color-mix(in_srgb,var(--status-bad)_35%,transparent)] bg-[var(--status-bad-muted)] px-3 py-2 text-sm text-status-bad"
            >
              {submitError}
            </div>
          )}

          <Button
            type="submit"
            size="lg"
            className="w-full font-semibold hover:bg-accent-pressed active:scale-[0.98]"
            isLoading={isSubmitting}
            disabled={isSubmitting}
          >
            Sign in
          </Button>
        </form>
      </Card>

      <p className="text-center text-sm text-muted">
        New here?{' '}
        <Link
          to="/register"
          className="font-medium text-accent transition-colors hover:text-accent-hover hover:underline"
        >
          Create an account
        </Link>
      </p>

      {showTestUsers && testUserLabel && testUserEmail && (
        <Card title="Development Only">
          <div className="flex flex-col gap-2 text-sm text-muted">
            <div className="flex items-center gap-2">
              <Badge variant="warning">Dev</Badge>
              <span>Example test account</span>
            </div>
            <p>
              <span className="font-medium text-foreground">{testUserLabel}:</span>{' '}
              <a
                href={`mailto:${testUserEmail}`}
                className="text-accent transition-colors hover:text-accent-hover hover:underline"
              >
                {testUserEmail}
              </a>
            </p>
            <p>
              <span className="font-medium text-foreground">Password:</span> ——
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}
