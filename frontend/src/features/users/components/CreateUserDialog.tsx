import { type FormEvent, useEffect, useId, useRef, useState } from 'react'

import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Spinner from '@/components/ui/Spinner'
import { cn } from '@/utils/cn'

import { EMAIL_PATTERN } from '../constants'
import type { Role } from '../types'

export interface CreateUserDialogProps {
  isOpen: boolean
  isSubmitting: boolean
  roles: Role[]
  rolesLoading: boolean
  error: string | null
  onClose: () => void
  onSubmit: (input: {
    full_name: string
    email: string
    password: string
    role: string
  }) => void
}

interface FieldErrors {
  full_name?: string
  email?: string
  password?: string
  role?: string
}

function validateFields(
  fullName: string,
  email: string,
  password: string,
  role: string,
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
  }

  if (!role) {
    errors.role = 'Role is required.'
  }

  return errors
}

export default function CreateUserDialog({
  isOpen,
  isSubmitting,
  roles,
  rolesLoading,
  error,
  onClose,
  onSubmit,
}: CreateUserDialogProps) {
  const titleId = useId()
  const roleSelectId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  useEffect(() => {
    if (!isOpen) {
      setFullName('')
      setEmail('')
      setPassword('')
      setRole('')
      setFieldErrors({})
      return
    }

    if (roles.length > 0 && !role) {
      setRole(roles[0]?.name ?? '')
    }
  }, [isOpen, roles, role])

  useEffect(() => {
    if (!isOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isSubmitting) onClose()
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, isSubmitting, onClose])

  if (!isOpen) return null

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const errors = validateFields(fullName, email, password, role)
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    setFieldErrors({})
    onSubmit({
      full_name: fullName.trim(),
      email: email.trim(),
      password,
      role,
    })
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={() => {
        if (!isSubmitting) onClose()
      }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cn(
          'w-full max-w-lg rounded-lg border border-neutral-200 bg-white p-6 shadow-lg',
          'dark:border-neutral-700 dark:bg-neutral-900',
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
          Create user
        </h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Add a new account and assign an initial role.
        </p>

        <form className="mt-4 flex flex-col gap-4" onSubmit={handleSubmit}>
          <Input
            label="Name"
            name="full_name"
            autoComplete="name"
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
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
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

          <div className="flex flex-col gap-1">
            <label
              htmlFor={roleSelectId}
              className="text-sm font-medium text-neutral-700 dark:text-neutral-200"
            >
              Role
            </label>
            {rolesLoading ? (
              <div className="flex items-center gap-2 py-2 text-sm text-neutral-500">
                <Spinner size="sm" label="Loading roles" />
                Loading roles…
              </div>
            ) : (
              <select
                id={roleSelectId}
                name="role"
                value={role}
                disabled={isSubmitting || roles.length === 0}
                aria-invalid={Boolean(fieldErrors.role)}
                className={cn(
                  'block w-full rounded-md border px-3 py-2 text-sm',
                  'bg-white text-neutral-900 dark:bg-neutral-800 dark:text-neutral-50',
                  fieldErrors.role
                    ? 'border-error-500'
                    : 'border-neutral-300 dark:border-neutral-600',
                  'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1',
                  'disabled:cursor-not-allowed disabled:opacity-50',
                )}
                onChange={(event) => {
                  setRole(event.target.value)
                  if (fieldErrors.role) {
                    setFieldErrors((prev) => {
                      const next = { ...prev }
                      delete next.role
                      return next
                    })
                  }
                }}
              >
                {roles.length === 0 ? (
                  <option value="">No roles available</option>
                ) : (
                  roles.map((item) => (
                    <option key={item.id} value={item.name}>
                      {item.name}
                    </option>
                  ))
                )}
              </select>
            )}
            {fieldErrors.role && (
              <p role="alert" className="text-xs text-error-500 dark:text-error-400">
                {fieldErrors.role}
              </p>
            )}
          </div>

          {error && (
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" disabled={isSubmitting} onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={isSubmitting}
              disabled={isSubmitting || rolesLoading || roles.length === 0}
            >
              Create user
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
