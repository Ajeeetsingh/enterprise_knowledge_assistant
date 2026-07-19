import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Button, Card, Input } from '@/components/ui'
import * as authApi from '@/services/authApi'
import type { ApiError } from '@/types'
import { toApiError } from '@/utils/apiError'

interface FieldErrors {
  full_name?: string
  email?: string
  password?: string
  confirmPassword?: string
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_HINT = 'At least 8 characters.'

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

function resolveRegisterErrorMessage(error: unknown): string {
  const apiError = isApiError(error) ? error : toApiError(error)

  if (apiError.status === 409) {
    return apiError.message || 'An account with this email already exists.'
  }

  if (apiError.status === 429) {
    return apiError.message || 'Too many registration attempts. Please try again later.'
  }

  if (apiError.status === 0) {
    return apiError.message || 'Network error — please check your connection.'
  }

  return apiError.message || 'Unable to create your account. Please try again.'
}

function validateFields(
  fullName: string,
  email: string,
  password: string,
  confirmPassword: string,
): FieldErrors {
  const errors: FieldErrors = {}

  if (!fullName.trim()) {
    errors.full_name = 'Name is required.'
  }

  const trimmedEmail = email.trim()
  if (!trimmedEmail) {
    errors.email = 'Email is required.'
  } else if (!EMAIL_PATTERN.test(trimmedEmail)) {
    errors.email = 'Enter a valid email address.'
  }

  if (!password) {
    errors.password = 'Password is required.'
  } else if (password.length < 8) {
    errors.password = PASSWORD_HINT
  }

  if (!confirmPassword) {
    errors.confirmPassword = 'Confirm your password.'
  } else if (confirmPassword !== password) {
    errors.confirmPassword = 'Passwords do not match.'
  }

  return errors
}

export default function RegisterPage() {
  const navigate = useNavigate()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitError(null)

    const errors = validateFields(fullName, email, password, confirmPassword)
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    setFieldErrors({})
    setIsSubmitting(true)

    try {
      await authApi.register({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
      })
      navigate('/login', {
        replace: true,
        state: {
          registrationSuccess: 'Account created successfully. You can now sign in.',
        },
      })
    } catch (error) {
      setSubmitError(resolveRegisterErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card title="Create account">
        <p className="mb-4 text-sm text-muted">
          Create your account to access your organisation&apos;s knowledge workspace.
        </p>

        <form
          className="flex flex-col gap-5"
          onSubmit={(event) => void handleSubmit(event)}
          noValidate
        >
          <Input
            label="Full name"
            name="full_name"
            autoComplete="name"
            placeholder="Jane Doe"
            value={fullName}
            disabled={isSubmitting}
            onChange={(event) => {
              setFullName(event.target.value)
              if (fieldErrors.full_name) {
                setFieldErrors((prev) => {
                  const next = { ...prev }
                  delete next.full_name
                  return next
                })
              }
            }}
            {...(fieldErrors.full_name ? { error: fieldErrors.full_name } : {})}
          />

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
            autoComplete="new-password"
            placeholder="Create a password"
            hint={PASSWORD_HINT}
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

          <Input
            label="Confirm password"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            placeholder="Confirm your password"
            value={confirmPassword}
            disabled={isSubmitting}
            onChange={(event) => {
              setConfirmPassword(event.target.value)
              if (fieldErrors.confirmPassword) {
                setFieldErrors((prev) => {
                  const next = { ...prev }
                  delete next.confirmPassword
                  return next
                })
              }
            }}
            {...(fieldErrors.confirmPassword ? { error: fieldErrors.confirmPassword } : {})}
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
            Create account
          </Button>
        </form>
      </Card>

      <p className="text-center text-sm text-muted">
        Already have an account?{' '}
        <Link
          to="/login"
          className="font-medium text-accent transition-colors hover:text-accent-hover hover:underline"
        >
          Sign in
        </Link>
      </p>
    </div>
  )
}
