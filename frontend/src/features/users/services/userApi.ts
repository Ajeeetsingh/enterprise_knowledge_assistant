/**
 * User administration API client (Phase 9.4A).
 */

import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  AssignRolesRequest,
  AssignRolesResponse,
  CreateUserRequest,
  CreateUserResponse,
  RoleListResponse,
  UpdateUserRequest,
  User,
  UserListResponse,
} from '../types'

async function request<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation()
  } catch (error) {
    throw toApiError(error)
  }
}

export async function getUsers(): Promise<UserListResponse> {
  return request(async () => {
    const { data } = await apiClient.get<UserListResponse>('/users')
    return data
  })
}

export async function getUser(userId: string): Promise<User> {
  return request(async () => {
    const { data } = await apiClient.get<User>(`/users/${userId}`)
    return data
  })
}

export async function createUser(body: CreateUserRequest): Promise<CreateUserResponse> {
  return request(async () => {
    const { data } = await apiClient.post<CreateUserResponse>('/users', body)
    return data
  })
}

/** Soft-deactivate a user (backend sets `is_active` to false). */
export async function disableUser(userId: string): Promise<User> {
  return request(async () => {
    const { data } = await apiClient.delete<User>(`/users/${userId}`)
    return data
  })
}

/** Update user profile fields including account status — PUT /users/{id}. */
export async function updateUser(userId: string, body: UpdateUserRequest): Promise<User> {
  return request(async () => {
    const { data } = await apiClient.put<User>(`/users/${userId}`, body)
    return data
  })
}

/** Assign roles after user creation — POST /users/{id}/roles. */
export async function assignUserRoles(
  userId: string,
  body: AssignRolesRequest,
): Promise<AssignRolesResponse> {
  return request(async () => {
    const { data } = await apiClient.post<AssignRolesResponse>(
      `/users/${userId}/roles`,
      body,
    )
    return data
  })
}

/** Remove a role from a user — DELETE /users/{id}/roles/{role_name}. */
export async function removeUserRole(
  userId: string,
  roleName: string,
): Promise<AssignRolesResponse> {
  return request(async () => {
    const { data } = await apiClient.delete<AssignRolesResponse>(
      `/users/${userId}/roles/${encodeURIComponent(roleName)}`,
    )
    return data
  })
}

/** List assignable roles — GET /roles (Admin only). */
export async function getRoles(): Promise<RoleListResponse> {
  return request(async () => {
    const { data } = await apiClient.get<RoleListResponse>('/roles')
    return data
  })
}
