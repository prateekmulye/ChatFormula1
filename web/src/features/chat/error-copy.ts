import { type StreamError } from "@/features/chat/stream-reducer";

/**
 * Human copy for stream errors. The gateway's AgentError.message is an
 * operator string (often a raw reason atom) — viewers get pit-wall language
 * instead, keyed on the normalized ErrorCode.
 */
export function humanizeStreamError(error: StreamError): string {
  switch (error.code) {
    case "UPSTREAM_UNAVAILABLE":
      return "The inference engine is unreachable — likely a free-tier cold start that ran long. Worth a re-send.";
    case "RATE_LIMITED":
      return "You're sending faster than the pit wall allows. Give it a moment, then re-send.";
    case "BUDGET_EXHAUSTED":
      return "Today's LLM budget is spent — the honest kind of out-of-fuel.";
    case "VALIDATION":
      // Validation messages are written for the viewer; pass them through.
      return error.message;
    case "INTERNAL":
      return "Something broke inside the gateway while streaming this answer.";
  }
}
