/** Resolved endpoint configuration. Defaults target a local gateway. */
export const GRAPHQL_HTTP_URL =
  import.meta.env.VITE_GRAPHQL_HTTP_URL ?? "http://localhost:4000/graphql";

export const GRAPHQL_WS_URL =
  import.meta.env.VITE_GRAPHQL_WS_URL ?? "ws://localhost:4000/socket/websocket";

/** Wake-on-paint target — `GET /up` on the gateway origin (ARCHITECTURE §2). */
export const WAKE_URL = new URL("/up", GRAPHQL_HTTP_URL).toString();

/** GraphiQL playground on the gateway origin — linked from About + footer. */
export const GRAPHIQL_URL = new URL("/graphiql", GRAPHQL_HTTP_URL).toString();

export const GITHUB_URL = "https://github.com/prateekmulye/ChatFormula1";

/**
 * The season with seeded data. The Jolpica nightly sync (Phase 5) will keep
 * this current; until then it matches the committed `data/` seeds.
 */
export const SEASON = 2025;
