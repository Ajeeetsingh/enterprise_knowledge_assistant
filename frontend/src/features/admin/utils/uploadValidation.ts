/**
 * Admin upload validation — shared with the documents feature selection helpers.
 */

export {
  MAX_BATCH_UPLOAD_FILES,
  MAX_DOCUMENT_FILE_SIZE_MB,
  formatFileSize,
  mergeUploadSelection,
  toSelectedUploadFile,
  validateDocumentFile,
  validateDocumentFileSelection,
  type SelectedUploadFile,
} from '@/features/documents/utils/uploadSelection'
