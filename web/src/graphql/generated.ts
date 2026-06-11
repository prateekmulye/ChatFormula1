import { gql } from '@apollo/client';
import * as Apollo from '@apollo/client';
export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
export type MakeEmpty<T extends { [key: string]: unknown }, K extends keyof T> = { [_ in K]?: never };
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
const defaultOptions = {} as const;
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: { input: string; output: string; }
  String: { input: string; output: string; }
  Boolean: { input: boolean; output: boolean; }
  Int: { input: number; output: number; }
  Float: { input: number; output: number; }
  /**
   * The `DateTime` scalar type represents a date and time in the UTC
   * timezone. The DateTime appears in a JSON response as an ISO8601 formatted
   * string, including UTC timezone ("Z"). The parsed date and time string will
   * be converted to UTC if there is an offset.
   */
  DateTime: { input: string; output: string; }
};

/** Stream-level error.  `retryable: true` means the client may call sendMessage again. */
export type AgentError = {
  __typename?: 'AgentError';
  code: ErrorCode;
  message: Scalars['String']['output'];
  messageId: Scalars['ID']['output'];
  retryable: Scalars['Boolean']['output'];
};

/**
 * Union of all event types published on the `agentStream` subscription.
 * Apollo resolves the concrete type via `__typename` (returned automatically
 * by Absinthe).
 */
export type AgentEvent = AgentError | MessageCompleted | NodeTransition | SourcesResolved | TokenDelta;

/** LangGraph pipeline node or gateway-synthesized state transition. */
export type AgentNode =
  /** LangGraph: analysing the query intent and routing decision. */
  | 'ANALYZE_QUERY'
  /** LangGraph: formatting and safety check on the generated response. */
  | 'FORMAT_RESPONSE'
  /** LangGraph: LLM generation (gpt-4o-mini). */
  | 'GENERATE'
  /** LangGraph: both vector and web retrieval running concurrently. */
  | 'PARALLEL_RETRIEVAL'
  /** LangGraph: ContextScore multi-factor re-ranking of retrieved chunks. */
  | 'RANK_CONTEXT'
  /** SHOWCASE mode: token-replaying a cached answer (Phase 5 only). */
  | 'REPLAYING_CACHE'
  /** LangGraph: routing between retrieval strategies. */
  | 'ROUTE'
  /** LangGraph: Pinecone vector similarity search. */
  | 'VECTOR_SEARCH'
  /** Gateway-synthesized: Render agent is cold-starting (designed UX, not an error). */
  | 'WARMING_UP'
  /** LangGraph: Tavily web search. */
  | 'WEB_SEARCH';

/** Circuit breaker state for the Python agent upstream. */
export type BreakerState =
  /** Normal operation; requests pass through. */
  | 'CLOSED'
  /** Probe request allowed through to test recovery. */
  | 'HALF_OPEN'
  /** Failures threshold exceeded; requests short-circuit with UPSTREAM_UNAVAILABLE. */
  | 'OPEN';

export type Constructor = {
  __typename?: 'Constructor';
  /** All drivers belonging to this constructor. Dataloader-batched. */
  drivers?: Maybe<Array<Driver>>;
  /** An F1 constructor (team). */
  id: Scalars['ID']['output'];
  name: Scalars['String']['output'];
  nationality?: Maybe<Scalars['String']['output']>;
  points: Scalars['Float']['output'];
};

export type Conversation = {
  __typename?: 'Conversation';
  /** A chat conversation owned by the viewer. */
  id: Scalars['ID']['output'];
  insertedAt: Scalars['DateTime']['output'];
  messages: Array<Message>;
  title?: Maybe<Scalars['String']['output']>;
};


export type ConversationMessagesArgs = {
  before?: InputMaybe<Scalars['String']['input']>;
  first?: InputMaybe<Scalars['Int']['input']>;
};

export type Driver = {
  __typename?: 'Driver';
  code: Scalars['String']['output'];
  /** The driver's constructor (team). Dataloader-batched. */
  constructor: Constructor;
  fullName: Scalars['String']['output'];
  /** An F1 driver. */
  id: Scalars['ID']['output'];
  nationality: Scalars['String']['output'];
  number?: Maybe<Scalars['Int']['output']>;
  /** Race results, optionally filtered by season. Dataloader-batched. */
  results?: Maybe<Array<RaceResult>>;
};


export type DriverResultsArgs = {
  season?: InputMaybe<Scalars['Int']['input']>;
};

/** Normalized error codes surfaced to GraphQL clients. */
export type ErrorCode =
  /** Daily LLM spend limit reached; SHOWCASE mode active (Phase 5). */
  | 'BUDGET_EXHAUSTED'
  /** Unexpected gateway or agent error. */
  | 'INTERNAL'
  /** The viewer has exceeded their request quota. */
  | 'RATE_LIMITED'
  /** The Python inference service is unreachable or returned an error. */
  | 'UPSTREAM_UNAVAILABLE'
  /** Input failed validation (length, control chars, repetition). */
  | 'VALIDATION';

/** Result of enqueuing an ingest job. */
export type IngestJob = {
  __typename?: 'IngestJob';
  id: Scalars['ID']['output'];
  queuedAt: Scalars['DateTime']['output'];
  state: Scalars['String']['output'];
};

/** Allowlisted ingest sources for the triggerIngest mutation. */
export type IngestSource =
  /** Race calendar sync. */
  | 'CALENDAR'
  /** Historical F1 data ingestion. */
  | 'HISTORICAL'
  /** Tavily news ingestion (nightly Oban job). */
  | 'NEWS';

export type Message = {
  __typename?: 'Message';
  cached: Scalars['Boolean']['output'];
  content: Scalars['String']['output'];
  /** A single message in a conversation. */
  id: Scalars['ID']['output'];
  insertedAt: Scalars['DateTime']['output'];
  intent?: Maybe<Scalars['String']['output']>;
  latencyMs?: Maybe<Scalars['Int']['output']>;
  role: MessageRole;
  sources: Array<Source>;
  status: MessageStatus;
};

/**
 * The assistant message is complete.  The hydrated `message` is included so
 * Apollo can write it directly to the normalized cache — no follow-up query
 * needed.  On cache-hit paths the gateway synthesizes one TokenDelta before
 * this event so the frontend render path is uniform.
 */
export type MessageCompleted = {
  __typename?: 'MessageCompleted';
  cached: Scalars['Boolean']['output'];
  message: Message;
  messageId: Scalars['ID']['output'];
  usage?: Maybe<TokenUsage>;
};

/** The role of a message author. */
export type MessageRole =
  /** A response generated by the agent. */
  | 'ASSISTANT'
  /** A message sent by the viewer. */
  | 'USER';

/** Lifecycle status of a message. */
export type MessageStatus =
  /** Message content is final. */
  | 'COMPLETE'
  /** Agent call failed; content is the error summary. */
  | 'FAILED'
  /** Placeholder created; agent call not yet started. */
  | 'PENDING'
  /** Agent is actively streaming (Phase 3 only). */
  | 'STREAMING';

/** A LangGraph pipeline node has started executing. */
export type NodeTransition = {
  __typename?: 'NodeTransition';
  messageId: Scalars['ID']['output'];
  node: AgentNode;
  startedAt: Scalars['DateTime']['output'];
};

export type Race = {
  __typename?: 'Race';
  circuit: Scalars['String']['output'];
  country: Scalars['String']['output'];
  /** An F1 race event. */
  id: Scalars['ID']['output'];
  name: Scalars['String']['output'];
  /** Race results in finish order. Dataloader-batched. */
  results?: Maybe<Array<RaceResult>>;
  round: Scalars['Int']['output'];
  season: Scalars['Int']['output'];
  startsAt: Scalars['DateTime']['output'];
};

export type RaceResult = {
  __typename?: 'RaceResult';
  driver: Driver;
  finishPosition?: Maybe<Scalars['Int']['output']>;
  gridPosition?: Maybe<Scalars['Int']['output']>;
  /** A single driver's result in one race. */
  id: Scalars['ID']['output'];
  podium: Scalars['Boolean']['output'];
  points: Scalars['Float']['output'];
  race: Race;
};

/** Current rate-limit status for the authenticated viewer. */
export type RateLimitStatus = {
  __typename?: 'RateLimitStatus';
  limitPerHour: Scalars['Int']['output'];
  limitPerMinute: Scalars['Int']['output'];
  remainingHour: Scalars['Int']['output'];
  remainingMinute: Scalars['Int']['output'];
  resetsAt: Scalars['DateTime']['output'];
};

export type RootMutationType = {
  __typename?: 'RootMutationType';
  /** Delete a conversation owned by the viewer. */
  deleteConversation: Scalars['Boolean']['output'];
  /**
   * Send a message in a conversation.
   *
   * Phase 3: **async** — persists the message pair and immediately returns
   * `{userMessage, assistantMessageId}` (< 50 ms, no LLM work).  The caller
   * subscribes to `agentStream(messageId: <assistantMessageId>)` to receive
   * streaming events.
   *
   * Input validation: 1–2000 chars, no control characters, no excessive
   * character repetition.
   */
  sendMessage: SendMessagePayload;
  /** Create a new conversation for the current viewer. */
  startConversation: Conversation;
  /**
   * Submit thumbs-up/down feedback on an assistant message.
   * Idempotent per viewer+message — re-submitting updates the existing row.
   */
  submitFeedback: Scalars['Boolean']['output'];
  /**
   * Enqueues a news/data ingest Oban job.
   * Requires API key with scope 'admin:ingest'.
   */
  triggerIngest: IngestJob;
};


export type RootMutationTypeDeleteConversationArgs = {
  id: Scalars['ID']['input'];
};


export type RootMutationTypeSendMessageArgs = {
  content: Scalars['String']['input'];
  conversationId: Scalars['ID']['input'];
};


export type RootMutationTypeSubmitFeedbackArgs = {
  helpful: Scalars['Boolean']['input'];
  messageId: Scalars['ID']['input'];
};


export type RootMutationTypeTriggerIngestArgs = {
  source: IngestSource;
};

export type RootQueryType = {
  __typename?: 'RootQueryType';
  /** Fetch a conversation by ID. Returns null if not found or not owned by viewer. */
  conversation?: Maybe<Conversation>;
  /** List all conversations for the current viewer. */
  conversations: Array<Conversation>;
  /** Pre-warmed SHOWCASE question chips wired to cached answers. */
  demoQuestions: Array<Scalars['String']['output']>;
  /** Look up a driver by three-letter code (e.g. 'VER'). */
  driver?: Maybe<Driver>;
  /** List all drivers, optionally filtered by season. */
  drivers?: Maybe<Array<Driver>>;
  /** The next upcoming race (used for homepage countdown). */
  nextRace?: Maybe<Race>;
  /** List races for a season. */
  races: Array<Race>;
  /** Current rate-limit status for the viewer. */
  rateLimitStatus: RateLimitStatus;
  /** Championship standings for a season. Single aggregating query — N+1 free. */
  standings: Array<StandingRow>;
  /** Current system health — gateway, agent, database, and circuit breaker state. */
  systemHealth: SystemHealth;
  /**
   * BEAM + system telemetry for the public pit-wall panel.
   * Only telemetry-fed numbers — no theater (see ARCHITECTURE.md risk #12).
   */
  systemStats: SystemStats;
};


export type RootQueryTypeConversationArgs = {
  id: Scalars['ID']['input'];
};


export type RootQueryTypeDriverArgs = {
  code: Scalars['String']['input'];
};


export type RootQueryTypeDriversArgs = {
  season?: InputMaybe<Scalars['Int']['input']>;
};


export type RootQueryTypeRacesArgs = {
  season: Scalars['Int']['input'];
};


export type RootQueryTypeStandingsArgs = {
  season: Scalars['Int']['input'];
};

export type RootSubscriptionType = {
  __typename?: 'RootSubscriptionType';
  /**
   * Subscribe to streaming events for a single assistant message.
   *
   * Topic: `agent:<message_id>`.  The subscription delivers the `AgentEvent`
   * union: TokenDelta batches, NodeTransition (pipeline telemetry), SourcesResolved
   * (citation chips), MessageCompleted (final state), and AgentError.
   *
   * **Authorization:** the viewer token must own the message's conversation.
   * Cross-viewer subscriptions are rejected at subscribe time with an
   * `UNAUTHORIZED` error — this is enforced in the `config/2` callback below,
   * not in the resolver.
   *
   * **Replay on reconnect:** buffered events (with original seq values) are
   * sent to a re-subscribing client before the live publish path starts.
   * The Apollo reducer deduplicates by seq.
   */
  agentStream?: Maybe<AgentEvent>;
  /**
   * Subscribe to circuit breaker state changes.
   *
   * Published on every breaker transition (closed → open → half_open → closed).
   * Lets the React UI flip LIVE/DEGRADED service badges in real time.
   * No message_id argument needed — this is a global gateway health topic.
   */
  systemHealthChanged?: Maybe<SystemHealth>;
};


export type RootSubscriptionTypeAgentStreamArgs = {
  messageId: Scalars['ID']['input'];
};

/** Payload returned by the sendMessage mutation. */
export type SendMessagePayload = {
  __typename?: 'SendMessagePayload';
  assistantMessageId: Scalars['ID']['output'];
  userMessage: Message;
};

/** High-level service operating mode. */
export type ServiceMode =
  /** Circuit breaker open or partial degradation; service still operational. */
  | 'DEGRADED'
  /** Live LLM inference running normally. */
  | 'LIVE'
  /** Budget exhausted or agent down; Phase 5 cached-replay path active. */
  | 'SHOWCASE';

/** Health of an individual service component. */
export type ServiceStatus =
  | 'DEGRADED'
  | 'DOWN'
  | 'HEALTHY';

/** A retrieval source cited in an assistant response. */
export type Source = {
  __typename?: 'Source';
  kind: SourceKind;
  score?: Maybe<Scalars['Float']['output']>;
  snippet?: Maybe<Scalars['String']['output']>;
  title: Scalars['String']['output'];
  url?: Maybe<Scalars['String']['output']>;
};

/** Source kind from retrieval pipeline. */
export type SourceKind =
  /** Pinecone vector search result. */
  | 'VECTOR'
  /** Tavily web search result. */
  | 'WEB';

/** Retrieval context has been resolved; citation chips can render before the answer finishes. */
export type SourcesResolved = {
  __typename?: 'SourcesResolved';
  messageId: Scalars['ID']['output'];
  sources: Array<Source>;
};

/** A row in the championship standings for a given season. */
export type StandingRow = {
  __typename?: 'StandingRow';
  driver: Driver;
  podiums: Scalars['Int']['output'];
  points: Scalars['Float']['output'];
  position: Scalars['Int']['output'];
  wins: Scalars['Int']['output'];
};

/**
 * Snapshot of gateway and upstream health.  Published on state transitions
 * via the `systemHealthChanged` subscription.
 */
export type SystemHealth = {
  __typename?: 'SystemHealth';
  agentService: ServiceStatus;
  breakerState: BreakerState;
  database: ServiceStatus;
  gateway: ServiceStatus;
  mode: ServiceMode;
};

/**
 * Real-time BEAM + system statistics.  All fields are telemetry-fed — no
 * invented numbers.  Nullable fields return nil when no data is available yet
 * (e.g. p95FirstTokenMs before any stream has completed).
 */
export type SystemStats = {
  __typename?: 'SystemStats';
  /** Number of active Conversation.Server GenServers. */
  activeConversations: Scalars['Int']['output'];
  /** Total BEAM process count (VM-level). */
  beamProcessCount: Scalars['Int']['output'];
  /** Remaining daily LLM budget in USD. */
  dailyBudgetRemainingUsd: Scalars['Float']['output'];
  /** When the standings data was last synced from Jolpica/Ergast. Nil if never. */
  lastStandingsSyncAt?: Maybe<Scalars['DateTime']['output']>;
  /** LLM spend in USD today. */
  llmSpendTodayUsd: Scalars['Float']['output'];
  /** Oban jobs completed in the last 24 hours. */
  obanJobsCompleted24h: Scalars['Int']['output'];
  /** p95 first-token latency in ms (nil until at least 1 stream completes). */
  p95FirstTokenMs?: Maybe<Scalars['Int']['output']>;
  /** Mean tokens/second from recent streams (nil until at least 1 stream completes). */
  tokensPerSecond?: Maybe<Scalars['Float']['output']>;
  /** Seconds since the gateway started. */
  uptimeSeconds: Scalars['Int']['output'];
};

/**
 * One or more LLM tokens.  Delivery is micro-batched: the Conversation.Server
 * accumulates tokens for 40 ms or 12 tokens (whichever comes first) before a
 * single publish.  This amortises Absinthe.Subscription.publish overhead and
 * PubSub frame cost on the 256 MB Fly machine.
 *
 * `seq` is a monotonically increasing integer scoped to the assistant message.
 * Clients use it for idempotent-replay deduplication — on reconnect, replay
 * from the Conversation.Server buffer overlaps with live events; duplicates
 * are dropped by the seq guard in the Apollo reducer.
 */
export type TokenDelta = {
  __typename?: 'TokenDelta';
  messageId: Scalars['ID']['output'];
  seq: Scalars['Int']['output'];
  text: Scalars['String']['output'];
};

/** Token-level usage statistics from the LLM provider. */
export type TokenUsage = {
  __typename?: 'TokenUsage';
  completionTokens: Scalars['Int']['output'];
  estimatedCostUsd: Scalars['Float']['output'];
  promptTokens: Scalars['Int']['output'];
};

export type SourceFieldsFragment = { __typename?: 'Source', kind: SourceKind, title: string, url?: string | null, snippet?: string | null, score?: number | null };

export type MessageFieldsFragment = { __typename?: 'Message', id: string, role: MessageRole, content: string, status: MessageStatus, intent?: string | null, cached: boolean, latencyMs?: number | null, insertedAt: string, sources: Array<{ __typename?: 'Source', kind: SourceKind, title: string, url?: string | null, snippet?: string | null, score?: number | null }> };

export type SystemHealthFieldsFragment = { __typename?: 'SystemHealth', mode: ServiceMode, gateway: ServiceStatus, agentService: ServiceStatus, database: ServiceStatus, breakerState: BreakerState };

export type StandingsQueryVariables = Exact<{
  season: Scalars['Int']['input'];
}>;


export type StandingsQuery = { __typename?: 'RootQueryType', standings: Array<{ __typename?: 'StandingRow', position: number, points: number, wins: number, podiums: number, driver: { __typename?: 'Driver', id: string, code: string, number?: number | null, fullName: string, nationality: string, constructor: { __typename?: 'Constructor', id: string, name: string } } }> };

export type RacesQueryVariables = Exact<{
  season: Scalars['Int']['input'];
}>;


export type RacesQuery = { __typename?: 'RootQueryType', races: Array<{ __typename?: 'Race', id: string, season: number, round: number, name: string, circuit: string, country: string, startsAt: string }> };

export type NextRaceQueryVariables = Exact<{ [key: string]: never; }>;


export type NextRaceQuery = { __typename?: 'RootQueryType', nextRace?: { __typename?: 'Race', id: string, season: number, round: number, name: string, circuit: string, country: string, startsAt: string } | null };

export type DriversQueryVariables = Exact<{
  season?: InputMaybe<Scalars['Int']['input']>;
}>;


export type DriversQuery = { __typename?: 'RootQueryType', drivers?: Array<{ __typename?: 'Driver', id: string, code: string, number?: number | null, fullName: string, nationality: string, constructor: { __typename?: 'Constructor', id: string, name: string, points: number } }> | null };

export type DemoQuestionsQueryVariables = Exact<{ [key: string]: never; }>;


export type DemoQuestionsQuery = { __typename?: 'RootQueryType', demoQuestions: Array<string> };

export type ConversationMessagesQueryVariables = Exact<{
  id: Scalars['ID']['input'];
}>;


export type ConversationMessagesQuery = { __typename?: 'RootQueryType', conversation?: { __typename?: 'Conversation', id: string, title?: string | null, messages: Array<{ __typename?: 'Message', id: string, role: MessageRole, content: string, status: MessageStatus, intent?: string | null, cached: boolean, latencyMs?: number | null, insertedAt: string, sources: Array<{ __typename?: 'Source', kind: SourceKind, title: string, url?: string | null, snippet?: string | null, score?: number | null }> }> } | null };

export type StartConversationMutationVariables = Exact<{ [key: string]: never; }>;


export type StartConversationMutation = { __typename?: 'RootMutationType', startConversation: { __typename?: 'Conversation', id: string, title?: string | null, insertedAt: string } };

export type SendMessageMutationVariables = Exact<{
  conversationId: Scalars['ID']['input'];
  content: Scalars['String']['input'];
}>;


export type SendMessageMutation = { __typename?: 'RootMutationType', sendMessage: { __typename?: 'SendMessagePayload', assistantMessageId: string, userMessage: { __typename?: 'Message', id: string, role: MessageRole, content: string, status: MessageStatus, intent?: string | null, cached: boolean, latencyMs?: number | null, insertedAt: string, sources: Array<{ __typename?: 'Source', kind: SourceKind, title: string, url?: string | null, snippet?: string | null, score?: number | null }> } } };

export type AgentStreamSubscriptionVariables = Exact<{
  messageId: Scalars['ID']['input'];
}>;


export type AgentStreamSubscription = { __typename?: 'RootSubscriptionType', agentStream?: { __typename: 'AgentError', messageId: string, code: ErrorCode, retryable: boolean, errorMessage: string } | { __typename: 'MessageCompleted', messageId: string, cached: boolean, message: { __typename?: 'Message', id: string, role: MessageRole, content: string, status: MessageStatus, intent?: string | null, cached: boolean, latencyMs?: number | null, insertedAt: string, sources: Array<{ __typename?: 'Source', kind: SourceKind, title: string, url?: string | null, snippet?: string | null, score?: number | null }> }, usage?: { __typename?: 'TokenUsage', promptTokens: number, completionTokens: number, estimatedCostUsd: number } | null } | { __typename: 'NodeTransition', messageId: string, node: AgentNode, startedAt: string } | { __typename: 'SourcesResolved', messageId: string, sources: Array<{ __typename?: 'Source', kind: SourceKind, title: string, url?: string | null, snippet?: string | null, score?: number | null }> } | { __typename: 'TokenDelta', messageId: string, seq: number, text: string } | null };

export type SystemHealthQueryVariables = Exact<{ [key: string]: never; }>;


export type SystemHealthQuery = { __typename?: 'RootQueryType', systemHealth: { __typename?: 'SystemHealth', mode: ServiceMode, gateway: ServiceStatus, agentService: ServiceStatus, database: ServiceStatus, breakerState: BreakerState } };

export type SystemStatsFieldsFragment = { __typename?: 'SystemStats', activeConversations: number, beamProcessCount: number, uptimeSeconds: number, p95FirstTokenMs?: number | null, tokensPerSecond?: number | null, obanJobsCompleted24h: number, lastStandingsSyncAt?: string | null, llmSpendTodayUsd: number, dailyBudgetRemainingUsd: number };

export type SystemStatsQueryVariables = Exact<{ [key: string]: never; }>;


export type SystemStatsQuery = { __typename?: 'RootQueryType', systemStats: { __typename?: 'SystemStats', activeConversations: number, beamProcessCount: number, uptimeSeconds: number, p95FirstTokenMs?: number | null, tokensPerSecond?: number | null, obanJobsCompleted24h: number, lastStandingsSyncAt?: string | null, llmSpendTodayUsd: number, dailyBudgetRemainingUsd: number } };

export type SystemHealthChangedSubscriptionVariables = Exact<{ [key: string]: never; }>;


export type SystemHealthChangedSubscription = { __typename?: 'RootSubscriptionType', systemHealthChanged?: { __typename?: 'SystemHealth', mode: ServiceMode, gateway: ServiceStatus, agentService: ServiceStatus, database: ServiceStatus, breakerState: BreakerState } | null };

export type RateLimitStatusQueryVariables = Exact<{ [key: string]: never; }>;


export type RateLimitStatusQuery = { __typename?: 'RootQueryType', rateLimitStatus: { __typename?: 'RateLimitStatus', limitPerMinute: number, remainingMinute: number, limitPerHour: number, remainingHour: number, resetsAt: string } };

export const SourceFieldsFragmentDoc = gql`
    fragment SourceFields on Source {
  kind
  title
  url
  snippet
  score
}
    `;
export const MessageFieldsFragmentDoc = gql`
    fragment MessageFields on Message {
  id
  role
  content
  status
  intent
  cached
  latencyMs
  insertedAt
  sources {
    ...SourceFields
  }
}
    ${SourceFieldsFragmentDoc}`;
export const SystemHealthFieldsFragmentDoc = gql`
    fragment SystemHealthFields on SystemHealth {
  mode
  gateway
  agentService
  database
  breakerState
}
    `;
export const SystemStatsFieldsFragmentDoc = gql`
    fragment SystemStatsFields on SystemStats {
  activeConversations
  beamProcessCount
  uptimeSeconds
  p95FirstTokenMs
  tokensPerSecond
  obanJobsCompleted24h
  lastStandingsSyncAt
  llmSpendTodayUsd
  dailyBudgetRemainingUsd
}
    `;
export const StandingsDocument = gql`
    query Standings($season: Int!) {
  standings(season: $season) {
    position
    points
    wins
    podiums
    driver {
      id
      code
      number
      fullName
      nationality
      constructor {
        id
        name
      }
    }
  }
}
    `;

/**
 * __useStandingsQuery__
 *
 * To run a query within a React component, call `useStandingsQuery` and pass it any options that fit your needs.
 * When your component renders, `useStandingsQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useStandingsQuery({
 *   variables: {
 *      season: // value for 'season'
 *   },
 * });
 */
export function useStandingsQuery(baseOptions: Apollo.QueryHookOptions<StandingsQuery, StandingsQueryVariables> & ({ variables: StandingsQueryVariables; skip?: boolean; } | { skip: boolean; }) ) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<StandingsQuery, StandingsQueryVariables>(StandingsDocument, options);
      }
export function useStandingsLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<StandingsQuery, StandingsQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<StandingsQuery, StandingsQueryVariables>(StandingsDocument, options);
        }
// @ts-ignore
export function useStandingsSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<StandingsQuery, StandingsQueryVariables>): Apollo.UseSuspenseQueryResult<StandingsQuery, StandingsQueryVariables>;
export function useStandingsSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<StandingsQuery, StandingsQueryVariables>): Apollo.UseSuspenseQueryResult<StandingsQuery | undefined, StandingsQueryVariables>;
export function useStandingsSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<StandingsQuery, StandingsQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<StandingsQuery, StandingsQueryVariables>(StandingsDocument, options);
        }
export type StandingsQueryHookResult = ReturnType<typeof useStandingsQuery>;
export type StandingsLazyQueryHookResult = ReturnType<typeof useStandingsLazyQuery>;
export type StandingsSuspenseQueryHookResult = ReturnType<typeof useStandingsSuspenseQuery>;
export type StandingsQueryResult = Apollo.QueryResult<StandingsQuery, StandingsQueryVariables>;
export const RacesDocument = gql`
    query Races($season: Int!) {
  races(season: $season) {
    id
    season
    round
    name
    circuit
    country
    startsAt
  }
}
    `;

/**
 * __useRacesQuery__
 *
 * To run a query within a React component, call `useRacesQuery` and pass it any options that fit your needs.
 * When your component renders, `useRacesQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useRacesQuery({
 *   variables: {
 *      season: // value for 'season'
 *   },
 * });
 */
export function useRacesQuery(baseOptions: Apollo.QueryHookOptions<RacesQuery, RacesQueryVariables> & ({ variables: RacesQueryVariables; skip?: boolean; } | { skip: boolean; }) ) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<RacesQuery, RacesQueryVariables>(RacesDocument, options);
      }
export function useRacesLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<RacesQuery, RacesQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<RacesQuery, RacesQueryVariables>(RacesDocument, options);
        }
// @ts-ignore
export function useRacesSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<RacesQuery, RacesQueryVariables>): Apollo.UseSuspenseQueryResult<RacesQuery, RacesQueryVariables>;
export function useRacesSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<RacesQuery, RacesQueryVariables>): Apollo.UseSuspenseQueryResult<RacesQuery | undefined, RacesQueryVariables>;
export function useRacesSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<RacesQuery, RacesQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<RacesQuery, RacesQueryVariables>(RacesDocument, options);
        }
export type RacesQueryHookResult = ReturnType<typeof useRacesQuery>;
export type RacesLazyQueryHookResult = ReturnType<typeof useRacesLazyQuery>;
export type RacesSuspenseQueryHookResult = ReturnType<typeof useRacesSuspenseQuery>;
export type RacesQueryResult = Apollo.QueryResult<RacesQuery, RacesQueryVariables>;
export const NextRaceDocument = gql`
    query NextRace {
  nextRace {
    id
    season
    round
    name
    circuit
    country
    startsAt
  }
}
    `;

/**
 * __useNextRaceQuery__
 *
 * To run a query within a React component, call `useNextRaceQuery` and pass it any options that fit your needs.
 * When your component renders, `useNextRaceQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useNextRaceQuery({
 *   variables: {
 *   },
 * });
 */
export function useNextRaceQuery(baseOptions?: Apollo.QueryHookOptions<NextRaceQuery, NextRaceQueryVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<NextRaceQuery, NextRaceQueryVariables>(NextRaceDocument, options);
      }
export function useNextRaceLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<NextRaceQuery, NextRaceQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<NextRaceQuery, NextRaceQueryVariables>(NextRaceDocument, options);
        }
// @ts-ignore
export function useNextRaceSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<NextRaceQuery, NextRaceQueryVariables>): Apollo.UseSuspenseQueryResult<NextRaceQuery, NextRaceQueryVariables>;
export function useNextRaceSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<NextRaceQuery, NextRaceQueryVariables>): Apollo.UseSuspenseQueryResult<NextRaceQuery | undefined, NextRaceQueryVariables>;
export function useNextRaceSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<NextRaceQuery, NextRaceQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<NextRaceQuery, NextRaceQueryVariables>(NextRaceDocument, options);
        }
export type NextRaceQueryHookResult = ReturnType<typeof useNextRaceQuery>;
export type NextRaceLazyQueryHookResult = ReturnType<typeof useNextRaceLazyQuery>;
export type NextRaceSuspenseQueryHookResult = ReturnType<typeof useNextRaceSuspenseQuery>;
export type NextRaceQueryResult = Apollo.QueryResult<NextRaceQuery, NextRaceQueryVariables>;
export const DriversDocument = gql`
    query Drivers($season: Int) {
  drivers(season: $season) {
    id
    code
    number
    fullName
    nationality
    constructor {
      id
      name
      points
    }
  }
}
    `;

/**
 * __useDriversQuery__
 *
 * To run a query within a React component, call `useDriversQuery` and pass it any options that fit your needs.
 * When your component renders, `useDriversQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useDriversQuery({
 *   variables: {
 *      season: // value for 'season'
 *   },
 * });
 */
export function useDriversQuery(baseOptions?: Apollo.QueryHookOptions<DriversQuery, DriversQueryVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<DriversQuery, DriversQueryVariables>(DriversDocument, options);
      }
export function useDriversLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<DriversQuery, DriversQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<DriversQuery, DriversQueryVariables>(DriversDocument, options);
        }
// @ts-ignore
export function useDriversSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<DriversQuery, DriversQueryVariables>): Apollo.UseSuspenseQueryResult<DriversQuery, DriversQueryVariables>;
export function useDriversSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<DriversQuery, DriversQueryVariables>): Apollo.UseSuspenseQueryResult<DriversQuery | undefined, DriversQueryVariables>;
export function useDriversSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<DriversQuery, DriversQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<DriversQuery, DriversQueryVariables>(DriversDocument, options);
        }
export type DriversQueryHookResult = ReturnType<typeof useDriversQuery>;
export type DriversLazyQueryHookResult = ReturnType<typeof useDriversLazyQuery>;
export type DriversSuspenseQueryHookResult = ReturnType<typeof useDriversSuspenseQuery>;
export type DriversQueryResult = Apollo.QueryResult<DriversQuery, DriversQueryVariables>;
export const DemoQuestionsDocument = gql`
    query DemoQuestions {
  demoQuestions
}
    `;

/**
 * __useDemoQuestionsQuery__
 *
 * To run a query within a React component, call `useDemoQuestionsQuery` and pass it any options that fit your needs.
 * When your component renders, `useDemoQuestionsQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useDemoQuestionsQuery({
 *   variables: {
 *   },
 * });
 */
export function useDemoQuestionsQuery(baseOptions?: Apollo.QueryHookOptions<DemoQuestionsQuery, DemoQuestionsQueryVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<DemoQuestionsQuery, DemoQuestionsQueryVariables>(DemoQuestionsDocument, options);
      }
export function useDemoQuestionsLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<DemoQuestionsQuery, DemoQuestionsQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<DemoQuestionsQuery, DemoQuestionsQueryVariables>(DemoQuestionsDocument, options);
        }
// @ts-ignore
export function useDemoQuestionsSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<DemoQuestionsQuery, DemoQuestionsQueryVariables>): Apollo.UseSuspenseQueryResult<DemoQuestionsQuery, DemoQuestionsQueryVariables>;
export function useDemoQuestionsSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<DemoQuestionsQuery, DemoQuestionsQueryVariables>): Apollo.UseSuspenseQueryResult<DemoQuestionsQuery | undefined, DemoQuestionsQueryVariables>;
export function useDemoQuestionsSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<DemoQuestionsQuery, DemoQuestionsQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<DemoQuestionsQuery, DemoQuestionsQueryVariables>(DemoQuestionsDocument, options);
        }
export type DemoQuestionsQueryHookResult = ReturnType<typeof useDemoQuestionsQuery>;
export type DemoQuestionsLazyQueryHookResult = ReturnType<typeof useDemoQuestionsLazyQuery>;
export type DemoQuestionsSuspenseQueryHookResult = ReturnType<typeof useDemoQuestionsSuspenseQuery>;
export type DemoQuestionsQueryResult = Apollo.QueryResult<DemoQuestionsQuery, DemoQuestionsQueryVariables>;
export const ConversationMessagesDocument = gql`
    query ConversationMessages($id: ID!) {
  conversation(id: $id) {
    id
    title
    messages {
      ...MessageFields
    }
  }
}
    ${MessageFieldsFragmentDoc}`;

/**
 * __useConversationMessagesQuery__
 *
 * To run a query within a React component, call `useConversationMessagesQuery` and pass it any options that fit your needs.
 * When your component renders, `useConversationMessagesQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useConversationMessagesQuery({
 *   variables: {
 *      id: // value for 'id'
 *   },
 * });
 */
export function useConversationMessagesQuery(baseOptions: Apollo.QueryHookOptions<ConversationMessagesQuery, ConversationMessagesQueryVariables> & ({ variables: ConversationMessagesQueryVariables; skip?: boolean; } | { skip: boolean; }) ) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<ConversationMessagesQuery, ConversationMessagesQueryVariables>(ConversationMessagesDocument, options);
      }
export function useConversationMessagesLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<ConversationMessagesQuery, ConversationMessagesQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<ConversationMessagesQuery, ConversationMessagesQueryVariables>(ConversationMessagesDocument, options);
        }
// @ts-ignore
export function useConversationMessagesSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<ConversationMessagesQuery, ConversationMessagesQueryVariables>): Apollo.UseSuspenseQueryResult<ConversationMessagesQuery, ConversationMessagesQueryVariables>;
export function useConversationMessagesSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<ConversationMessagesQuery, ConversationMessagesQueryVariables>): Apollo.UseSuspenseQueryResult<ConversationMessagesQuery | undefined, ConversationMessagesQueryVariables>;
export function useConversationMessagesSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<ConversationMessagesQuery, ConversationMessagesQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<ConversationMessagesQuery, ConversationMessagesQueryVariables>(ConversationMessagesDocument, options);
        }
export type ConversationMessagesQueryHookResult = ReturnType<typeof useConversationMessagesQuery>;
export type ConversationMessagesLazyQueryHookResult = ReturnType<typeof useConversationMessagesLazyQuery>;
export type ConversationMessagesSuspenseQueryHookResult = ReturnType<typeof useConversationMessagesSuspenseQuery>;
export type ConversationMessagesQueryResult = Apollo.QueryResult<ConversationMessagesQuery, ConversationMessagesQueryVariables>;
export const StartConversationDocument = gql`
    mutation StartConversation {
  startConversation {
    id
    title
    insertedAt
  }
}
    `;
export type StartConversationMutationFn = Apollo.MutationFunction<StartConversationMutation, StartConversationMutationVariables>;

/**
 * __useStartConversationMutation__
 *
 * To run a mutation, you first call `useStartConversationMutation` within a React component and pass it any options that fit your needs.
 * When your component renders, `useStartConversationMutation` returns a tuple that includes:
 * - A mutate function that you can call at any time to execute the mutation
 * - An object with fields that represent the current status of the mutation's execution
 *
 * @param baseOptions options that will be passed into the mutation, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options-2;
 *
 * @example
 * const [startConversationMutation, { data, loading, error }] = useStartConversationMutation({
 *   variables: {
 *   },
 * });
 */
export function useStartConversationMutation(baseOptions?: Apollo.MutationHookOptions<StartConversationMutation, StartConversationMutationVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useMutation<StartConversationMutation, StartConversationMutationVariables>(StartConversationDocument, options);
      }
export type StartConversationMutationHookResult = ReturnType<typeof useStartConversationMutation>;
export type StartConversationMutationResult = Apollo.MutationResult<StartConversationMutation>;
export type StartConversationMutationOptions = Apollo.BaseMutationOptions<StartConversationMutation, StartConversationMutationVariables>;
export const SendMessageDocument = gql`
    mutation SendMessage($conversationId: ID!, $content: String!) {
  sendMessage(conversationId: $conversationId, content: $content) {
    userMessage {
      ...MessageFields
    }
    assistantMessageId
  }
}
    ${MessageFieldsFragmentDoc}`;
export type SendMessageMutationFn = Apollo.MutationFunction<SendMessageMutation, SendMessageMutationVariables>;

/**
 * __useSendMessageMutation__
 *
 * To run a mutation, you first call `useSendMessageMutation` within a React component and pass it any options that fit your needs.
 * When your component renders, `useSendMessageMutation` returns a tuple that includes:
 * - A mutate function that you can call at any time to execute the mutation
 * - An object with fields that represent the current status of the mutation's execution
 *
 * @param baseOptions options that will be passed into the mutation, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options-2;
 *
 * @example
 * const [sendMessageMutation, { data, loading, error }] = useSendMessageMutation({
 *   variables: {
 *      conversationId: // value for 'conversationId'
 *      content: // value for 'content'
 *   },
 * });
 */
export function useSendMessageMutation(baseOptions?: Apollo.MutationHookOptions<SendMessageMutation, SendMessageMutationVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useMutation<SendMessageMutation, SendMessageMutationVariables>(SendMessageDocument, options);
      }
export type SendMessageMutationHookResult = ReturnType<typeof useSendMessageMutation>;
export type SendMessageMutationResult = Apollo.MutationResult<SendMessageMutation>;
export type SendMessageMutationOptions = Apollo.BaseMutationOptions<SendMessageMutation, SendMessageMutationVariables>;
export const AgentStreamDocument = gql`
    subscription AgentStream($messageId: ID!) {
  agentStream(messageId: $messageId) {
    __typename
    ... on TokenDelta {
      messageId
      seq
      text
    }
    ... on NodeTransition {
      messageId
      node
      startedAt
    }
    ... on SourcesResolved {
      messageId
      sources {
        ...SourceFields
      }
    }
    ... on MessageCompleted {
      messageId
      cached
      message {
        ...MessageFields
      }
      usage {
        promptTokens
        completionTokens
        estimatedCostUsd
      }
    }
    ... on AgentError {
      messageId
      code
      errorMessage: message
      retryable
    }
  }
}
    ${SourceFieldsFragmentDoc}
${MessageFieldsFragmentDoc}`;

/**
 * __useAgentStreamSubscription__
 *
 * To run a query within a React component, call `useAgentStreamSubscription` and pass it any options that fit your needs.
 * When your component renders, `useAgentStreamSubscription` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the subscription, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useAgentStreamSubscription({
 *   variables: {
 *      messageId: // value for 'messageId'
 *   },
 * });
 */
export function useAgentStreamSubscription(baseOptions: Apollo.SubscriptionHookOptions<AgentStreamSubscription, AgentStreamSubscriptionVariables> & ({ variables: AgentStreamSubscriptionVariables; skip?: boolean; } | { skip: boolean; }) ) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useSubscription<AgentStreamSubscription, AgentStreamSubscriptionVariables>(AgentStreamDocument, options);
      }
export type AgentStreamSubscriptionHookResult = ReturnType<typeof useAgentStreamSubscription>;
export type AgentStreamSubscriptionResult = Apollo.SubscriptionResult<AgentStreamSubscription>;
export const SystemHealthDocument = gql`
    query SystemHealth {
  systemHealth {
    ...SystemHealthFields
  }
}
    ${SystemHealthFieldsFragmentDoc}`;

/**
 * __useSystemHealthQuery__
 *
 * To run a query within a React component, call `useSystemHealthQuery` and pass it any options that fit your needs.
 * When your component renders, `useSystemHealthQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useSystemHealthQuery({
 *   variables: {
 *   },
 * });
 */
export function useSystemHealthQuery(baseOptions?: Apollo.QueryHookOptions<SystemHealthQuery, SystemHealthQueryVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<SystemHealthQuery, SystemHealthQueryVariables>(SystemHealthDocument, options);
      }
export function useSystemHealthLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<SystemHealthQuery, SystemHealthQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<SystemHealthQuery, SystemHealthQueryVariables>(SystemHealthDocument, options);
        }
// @ts-ignore
export function useSystemHealthSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<SystemHealthQuery, SystemHealthQueryVariables>): Apollo.UseSuspenseQueryResult<SystemHealthQuery, SystemHealthQueryVariables>;
export function useSystemHealthSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<SystemHealthQuery, SystemHealthQueryVariables>): Apollo.UseSuspenseQueryResult<SystemHealthQuery | undefined, SystemHealthQueryVariables>;
export function useSystemHealthSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<SystemHealthQuery, SystemHealthQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<SystemHealthQuery, SystemHealthQueryVariables>(SystemHealthDocument, options);
        }
export type SystemHealthQueryHookResult = ReturnType<typeof useSystemHealthQuery>;
export type SystemHealthLazyQueryHookResult = ReturnType<typeof useSystemHealthLazyQuery>;
export type SystemHealthSuspenseQueryHookResult = ReturnType<typeof useSystemHealthSuspenseQuery>;
export type SystemHealthQueryResult = Apollo.QueryResult<SystemHealthQuery, SystemHealthQueryVariables>;
export const SystemStatsDocument = gql`
    query SystemStats {
  systemStats {
    ...SystemStatsFields
  }
}
    ${SystemStatsFieldsFragmentDoc}`;

/**
 * __useSystemStatsQuery__
 *
 * To run a query within a React component, call `useSystemStatsQuery` and pass it any options that fit your needs.
 * When your component renders, `useSystemStatsQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useSystemStatsQuery({
 *   variables: {
 *   },
 * });
 */
export function useSystemStatsQuery(baseOptions?: Apollo.QueryHookOptions<SystemStatsQuery, SystemStatsQueryVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<SystemStatsQuery, SystemStatsQueryVariables>(SystemStatsDocument, options);
      }
export function useSystemStatsLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<SystemStatsQuery, SystemStatsQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<SystemStatsQuery, SystemStatsQueryVariables>(SystemStatsDocument, options);
        }
// @ts-ignore
export function useSystemStatsSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<SystemStatsQuery, SystemStatsQueryVariables>): Apollo.UseSuspenseQueryResult<SystemStatsQuery, SystemStatsQueryVariables>;
export function useSystemStatsSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<SystemStatsQuery, SystemStatsQueryVariables>): Apollo.UseSuspenseQueryResult<SystemStatsQuery | undefined, SystemStatsQueryVariables>;
export function useSystemStatsSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<SystemStatsQuery, SystemStatsQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<SystemStatsQuery, SystemStatsQueryVariables>(SystemStatsDocument, options);
        }
export type SystemStatsQueryHookResult = ReturnType<typeof useSystemStatsQuery>;
export type SystemStatsLazyQueryHookResult = ReturnType<typeof useSystemStatsLazyQuery>;
export type SystemStatsSuspenseQueryHookResult = ReturnType<typeof useSystemStatsSuspenseQuery>;
export type SystemStatsQueryResult = Apollo.QueryResult<SystemStatsQuery, SystemStatsQueryVariables>;
export const SystemHealthChangedDocument = gql`
    subscription SystemHealthChanged {
  systemHealthChanged {
    ...SystemHealthFields
  }
}
    ${SystemHealthFieldsFragmentDoc}`;

/**
 * __useSystemHealthChangedSubscription__
 *
 * To run a query within a React component, call `useSystemHealthChangedSubscription` and pass it any options that fit your needs.
 * When your component renders, `useSystemHealthChangedSubscription` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the subscription, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useSystemHealthChangedSubscription({
 *   variables: {
 *   },
 * });
 */
export function useSystemHealthChangedSubscription(baseOptions?: Apollo.SubscriptionHookOptions<SystemHealthChangedSubscription, SystemHealthChangedSubscriptionVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useSubscription<SystemHealthChangedSubscription, SystemHealthChangedSubscriptionVariables>(SystemHealthChangedDocument, options);
      }
export type SystemHealthChangedSubscriptionHookResult = ReturnType<typeof useSystemHealthChangedSubscription>;
export type SystemHealthChangedSubscriptionResult = Apollo.SubscriptionResult<SystemHealthChangedSubscription>;
export const RateLimitStatusDocument = gql`
    query RateLimitStatus {
  rateLimitStatus {
    limitPerMinute
    remainingMinute
    limitPerHour
    remainingHour
    resetsAt
  }
}
    `;

/**
 * __useRateLimitStatusQuery__
 *
 * To run a query within a React component, call `useRateLimitStatusQuery` and pass it any options that fit your needs.
 * When your component renders, `useRateLimitStatusQuery` returns an object from Apollo Client that contains loading, error, and data properties
 * you can use to render your UI.
 *
 * @param baseOptions options that will be passed into the query, supported options are listed on: https://www.apollographql.com/docs/react/api/react-hooks/#options;
 *
 * @example
 * const { data, loading, error } = useRateLimitStatusQuery({
 *   variables: {
 *   },
 * });
 */
export function useRateLimitStatusQuery(baseOptions?: Apollo.QueryHookOptions<RateLimitStatusQuery, RateLimitStatusQueryVariables>) {
        const options = {...defaultOptions, ...baseOptions}
        return Apollo.useQuery<RateLimitStatusQuery, RateLimitStatusQueryVariables>(RateLimitStatusDocument, options);
      }
export function useRateLimitStatusLazyQuery(baseOptions?: Apollo.LazyQueryHookOptions<RateLimitStatusQuery, RateLimitStatusQueryVariables>) {
          const options = {...defaultOptions, ...baseOptions}
          return Apollo.useLazyQuery<RateLimitStatusQuery, RateLimitStatusQueryVariables>(RateLimitStatusDocument, options);
        }
// @ts-ignore
export function useRateLimitStatusSuspenseQuery(baseOptions?: Apollo.SuspenseQueryHookOptions<RateLimitStatusQuery, RateLimitStatusQueryVariables>): Apollo.UseSuspenseQueryResult<RateLimitStatusQuery, RateLimitStatusQueryVariables>;
export function useRateLimitStatusSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<RateLimitStatusQuery, RateLimitStatusQueryVariables>): Apollo.UseSuspenseQueryResult<RateLimitStatusQuery | undefined, RateLimitStatusQueryVariables>;
export function useRateLimitStatusSuspenseQuery(baseOptions?: Apollo.SkipToken | Apollo.SuspenseQueryHookOptions<RateLimitStatusQuery, RateLimitStatusQueryVariables>) {
          const options = baseOptions === Apollo.skipToken ? baseOptions : {...defaultOptions, ...baseOptions}
          return Apollo.useSuspenseQuery<RateLimitStatusQuery, RateLimitStatusQueryVariables>(RateLimitStatusDocument, options);
        }
export type RateLimitStatusQueryHookResult = ReturnType<typeof useRateLimitStatusQuery>;
export type RateLimitStatusLazyQueryHookResult = ReturnType<typeof useRateLimitStatusLazyQuery>;
export type RateLimitStatusSuspenseQueryHookResult = ReturnType<typeof useRateLimitStatusSuspenseQuery>;
export type RateLimitStatusQueryResult = Apollo.QueryResult<RateLimitStatusQuery, RateLimitStatusQueryVariables>;