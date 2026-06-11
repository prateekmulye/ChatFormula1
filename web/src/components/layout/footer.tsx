import { Link } from "react-router-dom";

import { CautionTriangleIcon } from "@/components/icons";
import { GITHUB_URL, GRAPHIQL_URL } from "@/lib/env";

/**
 * Footer disclaimer (DESIGN.md §3.5): persistent, readable text on every
 * route — never a tooltip (anti-slop rule 13).
 */
export function Footer() {
  return (
    <footer className="border-t border-hairline bg-surface-1 pb-16 md:pb-0">
      <div className="mx-auto max-w-[1200px] space-y-3 px-4 py-5">
        <p className="flex items-start gap-2 text-meta leading-relaxed text-text-dim">
          <CautionTriangleIcon className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
          <span>
            ChatFormula1 is an unofficial fan project. Not affiliated with, endorsed by, or
            connected to Formula 1, the FIA, or any F1 team.
          </span>
        </p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-hairline pt-3">
          <a
            className="text-meta text-text-dim underline-offset-4 hover:text-azure hover:underline"
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub<span className="sr-only"> (opens in a new tab)</span>
          </a>
          <Link
            className="text-meta text-text-dim underline-offset-4 hover:text-azure hover:underline"
            to="/about"
          >
            Architecture
          </Link>
          <a
            className="text-meta text-text-dim underline-offset-4 hover:text-azure hover:underline"
            href={GRAPHIQL_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            GraphiQL<span className="sr-only"> (opens in a new tab)</span>
          </a>
          <span className="tabular ml-auto font-mono text-micro text-text-faint">
            build {__BUILD_HASH__}
          </span>
        </div>
      </div>
    </footer>
  );
}
