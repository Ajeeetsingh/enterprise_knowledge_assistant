export interface KnowledgeDomain {
  id: string
  name: string
  description: string | null
}

export interface KnowledgeDomainListResponse {
  items: KnowledgeDomain[]
}

export interface KnowledgeDomainCreateRequest {
  name: string
  description?: string | null
}
