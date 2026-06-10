import { ArrowRightIcon } from "@/components/icons";
import { GITHUB_URL, GRAPHIQL_URL } from "@/lib/env";
import { PageHeading } from "@/routes/page-chrome";

const STACK = [
  ["web/", "React 18 · TypeScript · Apollo (split link: HTTP + graphql-ws) · Tailwind v4 · Motion"],
  ["gateway/", "Elixir/OTP · Phoenix · Absinthe GraphQL · per-conversation GenServers · circuit breaker"],
  ["agent/", "Python 3.12 · FastAPI · LangGraph routed-RAG pipeline · Pinecone + Tavily retrieval"],
] as const;

function ExternalLink({ href, children }: { href: string; children: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex min-h-11 items-center gap-2 rounded-sm border border-hairline bg-surface-2 px-4 text-ui text-text transition-colors duration-120 hover:border-azure/50"
    >
      {children}
      <ArrowRightIcon className="h-4 w-4 text-azure" />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

export function AboutPage() {
  return (
    <div className="mx-auto max-w-[760px] space-y-8 px-4 py-8">
      <PageHeading title="What you're looking at" kicker="Architecture" />

      <div className="space-y-4 text-body text-text-dim">
        <p>
          ChatFormula1 is a one-author portfolio system: a streaming F1 chat where every answer is
          piped from a LangGraph retrieval pipeline through a supervised Elixir/OTP process tree
          into a GraphQL subscription — and the UI shows you which pipeline node is running while
          the tokens arrive.
        </p>
        <p>
          The telemetry strip, the status badge, and the ops panel are not decoration: they render
          the gateway&apos;s real <span className="font-mono text-meta">systemHealth</span> — circuit
          breaker state included. When the free-tier inference engine cold-starts, you see the
          lights-out sequence instead of a spinner, because the wait is part of the demo.
        </p>
      </div>

      <dl className="space-y-3">
        {STACK.map(([name, description]) => (
          <div key={name} className="rounded-lg border border-hairline bg-surface-1 px-4 py-3">
            <dt className="instrument text-meta text-azure">{name}</dt>
            <dd className="mt-1 text-meta leading-relaxed text-text-dim">{description}</dd>
          </div>
        ))}
      </dl>

      <div className="flex flex-wrap gap-3">
        <ExternalLink href={GITHUB_URL}>Read the source on GitHub</ExternalLink>
        <ExternalLink href={`${GITHUB_URL}/blob/main/docs/ARCHITECTURE.md`}>
          Architecture deep-dive
        </ExternalLink>
        <ExternalLink href={GRAPHIQL_URL}>Query it yourself — GraphiQL</ExternalLink>
      </div>
    </div>
  );
}
