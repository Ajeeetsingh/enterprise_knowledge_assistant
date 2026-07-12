/**
 * pdf.js worker configuration (react-pdf's officially recommended Vite setup).
 *
 * The worker MUST be the exact same version as the `pdfjs-dist` package that
 * `react-pdf` resolves at build time — otherwise pdf.js throws:
 *   UnknownErrorException: The API version "X" does not match the Worker
 *   version "Y".
 *
 * `new URL(..., import.meta.url)` resolves the worker file relative to this
 * module through Vite's module graph, so it always resolves to whichever
 * `pdfjs-dist` version is actually installed in node_modules — never a
 * hardcoded CDN version that can drift out of sync.
 */
import { pdfjs } from 'react-pdf'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()
