import { type FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { Badge, Button, Card, Input } from '@/components/ui'
import { useAuth } from '@/contexts/AuthContext'
import type { ApiError } from '@/types'
import { toApiError } from '@/utils/apiError'

interface LoginLocationState {
  from?: string
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

  const redirectPath = resolveRedirectPath(
    (location.state as LoginLocationState | null)?.from,
  )

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
        <form className="flex flex-col gap-4" onSubmit={(event) => void handleSubmit(event)} noValidate>
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
              className="rounded-md border border-error-500/30 bg-error-50 px-3 py-2 text-sm text-error-700 dark:bg-error-700/10 dark:text-error-400"
            >
              {submitError}
            </div>
          )}

          <Button type="submit" className="w-full" isLoading={isSubmitting} disabled={isSubmitting}>
            Sign in
          </Button>
        </form>
      </Card>

      {showTestUsers && testUserLabel && testUserEmail && (
        <Card title="Development Only">
          <div className="flex flex-col gap-2 text-sm text-neutral-600 dark:text-neutral-400">
            <div className="flex items-center gap-2">
              <Badge variant="warning">Dev</Badge>
              <span>Example test account</span>
            </div>
            <p>
              <span className="font-medium text-neutral-800 dark:text-neutral-200">
                {testUserLabel}:
              </span>{' '}
              <a
                href={`mailto:${testUserEmail}`}
                className="text-primary-600 hover:underline dark:text-primary-400"
              >
                {testUserEmail}
              </a>
            </p>
            <p>
              <span className="font-medium text-neutral-800 dark:text-neutral-200">
                Password:
              </span>{' '}
              ——
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}
