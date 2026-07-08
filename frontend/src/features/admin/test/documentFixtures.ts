import type { Document } from '@/features/documents/types'
import { DocumentStatus } from '@/features/documents/types'

import type { AdminDocumentRow } from '../utils/documentFilters'

export const mockAdminDocuments: AdminDocumentRow[] = [
  {
    document_id: 'doc-1',
    filename: 'Employee Handbook.pdf',
    status: DocumentStatus.Searchable,
    uploaded_at: '2026-06-01T10:00:00Z',
    uploaded_by: 'user-1',
    visibility: 'public',
  },
  {
    document_id: 'doc-2',
    filename: 'Finance Policy.pdf',
    status: DocumentStatus.Processing,
    uploaded_at: '2026-06-02T11:00:00Z',
    uploaded_by: 'user-2',
    visibility: 'restricted',
  },
  {
    document_id: 'doc-3',
    filename: 'HR Notes.txt',
    status: DocumentStatus.Failed,
    uploaded_at: '2026-06-03T12:00:00Z',
    uploaded_by: 'user-3',
    visibility: 'private',
  },
]

export function createDocument(overrides: Partial<AdminDocumentRow> = {}): AdminDocumentRow {
  return {
    document_id: 'doc-default',
    filename: 'Default Document.pdf',
    status: DocumentStatus.Searchable,
    uploaded_at: '2026-06-01T10:00:00Z',
    uploaded_by: 'user-default',
    visibility: 'public',
    ...overrides,
  }
}

export type { Document }
