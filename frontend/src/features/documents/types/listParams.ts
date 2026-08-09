export interface DocumentListParams {
  limit?: number
  offset?: number
  filename?: string
  status?: string
  /** When set, backend returns only documents in this Knowledge Domain. */
  domain_id?: string
}
