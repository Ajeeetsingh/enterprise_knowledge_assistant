/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_SHOW_TEST_USERS?: string
  readonly VITE_TEST_USER_LABEL?: string
  readonly VITE_TEST_USER_EMAIL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
