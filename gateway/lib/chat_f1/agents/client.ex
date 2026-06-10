defmodule ChatF1.Agents.Client do
  @moduledoc """
  HTTP client for the Python inference agent.

  Calls `POST /internal/chat` with a bearer token and a JSON body, then
  **aggregates** the NDJSON stream into a single result map.  Phase 2 is
  synchronous — the entire stream is consumed before returning.

  ## NDJSON event handling

  Events are parsed according to `docs/STREAMING_PROTOCOL.md`:

  | event          | action                                                    |
  |----------------|-----------------------------------------------------------|
  | `node_started` | ignored in Phase 2 (no subscription fan-out yet)         |
  | `sources`      | accumulated into the sources list                         |
  | `token`        | accumulated into the content buffer                       |
  | `complete`     | sets final content + cached flag + usage; terminates loop |
  | `error`        | returns `{:error, code, message, retryable}`              |

  Cache-hit semantics: a `complete` with `cached: true` and zero `token`
  events is valid.  The gateway stores the `complete.content` directly rather
  than the accumulated token buffer, so cache hits work naturally.

  ## Timeouts and failure modes

  * `recv_timeout: 30_000` — entire stream must complete within 30 s.
  * `connect_timeout: 5_000` — fail fast on Render cold-start before the
    circuit breaker (Phase 3) fires; for now the mutation returns a normalized
    UPSTREAM_UNAVAILABLE error.
  * On connection refused or timeout: `{:error, :upstream_unavailable}`.
  * On `error` event in stream: `{:error, :agent_error, code, message}`.
  """

  require Logger

  @connect_timeout 5_000
  @recv_timeout 30_000

  @type source :: %{
          kind: String.t(),
          title: String.t(),
          url: String.t() | nil,
          snippet: String.t() | nil,
          score: float() | nil
        }

  @type success_result :: %{
          content: String.t(),
          sources: [source()],
          cached: boolean(),
          intent: String.t() | nil,
          latency_ms: integer()
        }

  @doc """
  Sends a chat request to the agent and aggregates the NDJSON response.

  `history` is a list of `%{role: "user" | "assistant", content: String.t()}`.
  Returns `{:ok, result}` or `{:error, reason}`.

  The response body is collected in full (Req buffers streaming responses when
  `into:` is not specified) and then parsed line-by-line as NDJSON.  For Phase 2
  this is correct and simpler than a streaming accumulator; Phase 3 will use a
  `Task.Supervisor`-monitored `Req.into:` with per-event GenServer casts.
  """
  @spec chat(String.t(), [map()], String.t()) ::
          {:ok, success_result()} | {:error, atom() | {atom(), String.t()}}
  def chat(message, history, request_id) do
    agent_url = Application.fetch_env!(:chat_f1, :agent_url)
    token = Application.fetch_env!(:chat_f1, :internal_api_token)

    body = %{
      message: message,
      history: history,
      request_id: request_id
    }

    start_ms = System.monotonic_time(:millisecond)

    # Note: Req 0.5+ does not allow :finch + :connect_options simultaneously.
    # We configure the connection timeout via :connect_options only and let Req
    # use its default Finch pool (or the app's named pool if configured without
    # :connect_options at the Req.new/1 level in Phase 3).
    result =
      Req.post(
        agent_url <> "/internal/chat",
        json: body,
        headers: [{"authorization", "Bearer #{token}"}],
        connect_options: [timeout: @connect_timeout],
        receive_timeout: @recv_timeout
      )

    elapsed_ms = System.monotonic_time(:millisecond) - start_ms

    parse_result(result, elapsed_ms)
  end

  # ─── Result parsing ──────────────────────────────────────────────────────────

  defp parse_result({:ok, %Req.Response{status: 200, body: body}}, _elapsed_ms)
       when not is_binary(body) do
    # A 200 whose body isn't a raw binary means Req decoded something other
    # than the NDJSON stream we expect — treat it as a broken upstream, never
    # try to parse (or echo) the decoded term.
    {:error, :upstream_unavailable}
  end

  defp parse_result({:ok, %Req.Response{status: 200, body: ndjson}}, elapsed_ms) do
    acc = parse_ndjson(ndjson)

    cond do
      not is_nil(acc.error) ->
        error_ev = acc.error
        code = Map.get(error_ev, "code", "internal")
        msg = Map.get(error_ev, "message", "Agent error")
        {:error, {:agent_error, code, msg}}

      not is_nil(acc.complete) ->
        complete = acc.complete
        # complete.content is authoritative; token_buffer is a cross-check.
        content = Map.get(complete, "content", acc.token_buffer)
        cached = Map.get(complete, "cached", false)

        {:ok,
         %{
           content: content,
           sources: normalize_sources(acc.sources),
           cached: cached,
           intent: nil,
           latency_ms: elapsed_ms
         }}

      true ->
        {:error, :upstream_unavailable}
    end
  end

  defp parse_result({:ok, %Req.Response{status: 401}}, _elapsed) do
    Logger.error("Agent rejected bearer token — check INTERNAL_API_TOKEN config")
    {:error, :upstream_unavailable}
  end

  defp parse_result({:ok, %Req.Response{status: status}}, _elapsed) do
    Logger.error("Agent returned unexpected HTTP status: #{status}")
    {:error, :upstream_unavailable}
  end

  defp parse_result({:error, exception}, _elapsed) do
    Logger.warning("Agent HTTP call failed: #{Exception.message(exception)}")
    {:error, :upstream_unavailable}
  end

  # ─── NDJSON parser ────────────────────────────────────────────────────────────

  # Parses a complete NDJSON body (all lines received).
  # Returns the final accumulator state.
  defp parse_ndjson(body) do
    initial = %{token_buffer: "", sources: [], complete: nil, error: nil}

    body
    |> String.split("\n", trim: true)
    |> Enum.reduce_while(initial, &reduce_ndjson_line/2)
  end

  defp reduce_ndjson_line(line, acc) do
    case Jason.decode(line) do
      {:ok, event} -> dispatch_event(event, acc)
      {:error, _} -> {:cont, acc}
    end
  end

  defp dispatch_event(event, acc) do
    case handle_event(event, acc) do
      {:done, final} -> {:halt, final}
      {:cont, updated} -> {:cont, updated}
    end
  end

  defp handle_event(%{"event" => "token", "text" => text}, acc) do
    {:cont, %{acc | token_buffer: acc.token_buffer <> text}}
  end

  defp handle_event(%{"event" => "sources", "items" => items}, acc) do
    {:cont, %{acc | sources: items}}
  end

  defp handle_event(%{"event" => "node_started"}, acc), do: {:cont, acc}

  defp handle_event(%{"event" => "complete"} = ev, acc) do
    {:done, %{acc | complete: ev}}
  end

  defp handle_event(%{"event" => "error"} = ev, acc) do
    {:done, %{acc | error: ev}}
  end

  defp handle_event(_unknown, acc), do: {:cont, acc}

  defp normalize_sources(items) when is_list(items) do
    Enum.map(items, fn item ->
      %{
        kind: Map.get(item, "kind", "vector"),
        title: Map.get(item, "title", ""),
        url: Map.get(item, "url"),
        snippet: Map.get(item, "snippet"),
        score: Map.get(item, "score")
      }
    end)
  end

  defp normalize_sources(_), do: []
end
