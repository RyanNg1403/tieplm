/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly FRONTEND_PORT: string;
  readonly BACKEND_PORT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

