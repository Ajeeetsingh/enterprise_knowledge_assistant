export { buildDocumentViewerUrl } from './utils/buildViewerUrl'
export {
  buildCitationViewerParams,
  getCitationChunkId,
  getCitationDocumentId,
  resolveCitationDocumentId,
} from './services/citationDocumentResolver'
export { storeCitationHighlight, consumeCitationHighlight } from './utils/citationHighlightStorage'
export { openDocumentInNewTab } from './utils/openDocumentInNewTab'
export type {
  CitationHighlightResult,
  DocumentViewerHighlightTarget,
  DocumentViewerParams,
} from './types'
