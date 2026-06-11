/// <reference types="vite/client" />

/** Short git SHA injected by vite.config.ts `define` — shown in the footer. */
declare const __BUILD_HASH__: string;

interface ImportMetaEnv {
  /** GraphQL HTTP endpoint, e.g. http://localhost:4000/graphql */
  readonly VITE_GRAPHQL_HTTP_URL?: string;
  /** graphql-ws endpoint, e.g. ws://localhost:4000/socket/websocket */
  readonly VITE_GRAPHQL_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
