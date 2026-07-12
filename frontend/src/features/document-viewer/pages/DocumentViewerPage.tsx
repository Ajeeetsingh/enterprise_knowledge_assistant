import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { useToast } from '@/contexts/ToastContext'
import { useDocument } from '@/features/documents/hooks/useDocuments'
import { getApiErrorMessage } from '@/services/errorHandler'

import DocumentViewerLayout from '../components/DocumentViewerLayout'
import { useDocumentFileSource } from '../hooks/useDocumentFileSource'
import { fetchDocumentFileBlob, triggerBlobDownload } from '../services/documentFileApi'

function isPdfContentType(contentType: string): boolean {
  return contentType.toLowerCase().includes('pdf')
}

export default function DocumentViewerPage() {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const { showError } = useToast()
  const [isDownloading, setIsDownloading] = useState(false)

  const {
    data: detail,
    isLoading: isDetailLoading,
    isError: isDetailError,
    error: detailError,
  } = useDocument(documentId ?? null)

  const {
    fileUrl,
    isLoading: isFileLoading,
    isError: isFileError,
    error: fileError,
  } = useDocumentFileSource(documentId)

  async function handleDownload() {
    if (!documentId || !detail) return
    setIsDownloading(true)
    try {
      const blob = await fetchDocumentFileBlob(documentId, { download: true })
      triggerBlobDownload(blob, detail.filename)
    } catch (downloadError) {
      showError(getApiErrorMessage(downloadError))
    } finally {
      setIsDownloading(false)
    }
  }

  if (!documentId) {
    return (
      <Card>
        <p className="text-sm text-error-500">Missing document ID.</p>
        <Button className="mt-4" onClick={() => navigate('/documents')}>
          Back to documents
        </Button>
      </Card>
    )
  }

  if (isDetailLoading || isFileLoading) {
    return (
      <div className="flex h-full min-h-[50vh] flex-col gap-3 p-6" aria-busy="true">
        <div className="h-10 animate-pulse rounded-md bg-[var(--bg-overlay)]" />
        <div className="min-h-0 flex-1 animate-pulse rounded-md bg-[var(--bg-overlay)]" />
      </div>
    )
  }

  if (isDetailError || !detail) {
    return (
      <Card>
        <p role="alert" className="text-sm text-error-500">
          {getApiErrorMessage(detailError)}
        </p>
        <Button className="mt-4" onClick={() => navigate('/documents')}>
          Back to documents
        </Button>
      </Card>
    )
  }

  if (isFileError || !fileUrl) {
    return (
      <Card>
        <p role="alert" className="text-sm text-error-500">
          {getApiErrorMessage(fileError)}
        </p>
        <Button className="mt-4" onClick={() => navigate('/documents')}>
          Back to documents
        </Button>
      </Card>
    )
  }

  return (
    <DocumentViewerLayout
      detail={detail}
      fileUrl={fileUrl}
      isPdf={isPdfContentType(detail.content_type)}
      onBack={() => navigate('/documents')}
      onDownload={() => void handleDownload()}
      isDownloading={isDownloading}
    />
  )
}
