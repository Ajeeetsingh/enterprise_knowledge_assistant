/** Cross-cutting API error shape returned by {@link toApiError}. */
export interface ApiError {
  message: string
  status: number
}
