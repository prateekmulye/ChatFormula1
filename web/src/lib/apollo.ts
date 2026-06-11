import { ApolloClient, HttpLink, InMemoryCache, split } from "@apollo/client";
import { setContext } from "@apollo/client/link/context";
import { GraphQLWsLink } from "@apollo/client/link/subscriptions";
import { getMainDefinition } from "@apollo/client/utilities";
import { createClient } from "graphql-ws";

import possibleTypes from "@/graphql/possible-types";
import { GRAPHQL_HTTP_URL, GRAPHQL_WS_URL } from "@/lib/env";
import { getViewerToken, setViewerToken, waitForViewerToken } from "@/lib/viewer-token";

/**
 * Captures the viewer token echoed by the gateway on every HTTP response
 * (`x-viewer-token`, exposed via CORS) so the WS handshake can present it.
 */
const tokenCapturingFetch: typeof fetch = async (input, init) => {
  const response = await fetch(input, init);
  const echoed = response.headers.get("x-viewer-token");
  if (echoed !== null && echoed !== "") setViewerToken(echoed);
  return response;
};

const httpLink = new HttpLink({
  uri: GRAPHQL_HTTP_URL,
  credentials: "include",
  fetch: tokenCapturingFetch,
});

/** Bearer-token auth once a viewer token exists (cookie covers the first call). */
const authLink = setContext((_operation, prevContext) => {
  const token = getViewerToken();
  if (token === null) return prevContext;
  const previousHeaders = (prevContext as { headers?: Record<string, string> }).headers ?? {};
  return { headers: { ...previousHeaders, authorization: `Bearer ${token}` } };
});

/**
 * graphql-ws transport (ARCHITECTURE §4.6): the gateway speaks the standard
 * `graphql-ws` sub-protocol via absinthe_graphql_ws. The handshake REQUIRES
 * the viewer token, so connectionParams awaits the first HTTP response.
 * Lazy by default — the socket opens on the first subscription.
 */
const wsLink = new GraphQLWsLink(
  createClient({
    url: GRAPHQL_WS_URL,
    connectionParams: async () => ({ token: await waitForViewerToken() }),
    retryAttempts: 8,
    shouldRetry: () => true,
  }),
);

/** Split link: subscriptions over WS, queries/mutations over HTTP. */
const splitLink = split(
  ({ query }) => {
    const definition = getMainDefinition(query);
    return definition.kind === "OperationDefinition" && definition.operation === "subscription";
  },
  wsLink,
  authLink.concat(httpLink),
);

export const apolloClient = new ApolloClient({
  link: splitLink,
  cache: new InMemoryCache({ possibleTypes: possibleTypes.possibleTypes }),
});
