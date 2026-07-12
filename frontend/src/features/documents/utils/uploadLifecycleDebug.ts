import type { DocumentUploadResponse } from '../types'

/** Upload lifecycle states used for debug tracing. */
export type UploadLifecycleState =
  | 'Idle'
  | 'Uploading'
  | 'Uploaded'
  | 'Processing'
  | 'Indexed'
  | 'Completed'
  | 'Failed'

export function mapBackendStatusToLifecycleState(status: string): UploadLifecycleState {
  switch (status) {
    case 'searchable':
      return 'Completed'
    case 'indexed':
      return 'Indexed'
    case 'processing':
    case 'uploaded':
    case 'validated':
    case 'stored':
      return 'Processing'
    case 'failed':
    case 'failed_extraction':
    case 'failed_embedding':
    case 'failed_indexing':
    case 'retry_pending':
      return 'Failed'
    default:
      return 'Uploaded'
  }
}

export function lifecycleStateFromUploadResponse(
  response: DocumentUploadResponse,
): UploadLifecycleState {
  return mapBackendStatusToLifecycleState(String(response.status))
}

export function logUploadTransition(
  context: string,
  state: UploadLifecycleState,
  details: Record<string, unknown> = {},
): void {
  const payload = {
    state,
    context,
    at: new Date().toISOString(),
    ...details,
  }

  if (state === 'Failed') {
    console.error('[upload-lifecycle]', payload)
    return
  }

  console.info('[upload-lifecycle]', payload)
}
