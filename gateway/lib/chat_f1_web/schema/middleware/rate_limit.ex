defmodule ChatF1Web.Schema.Middleware.RateLimit do
  @moduledoc """
  Absinthe middleware: enforces the ETS token-bucket rate limit.

  Applied after `ViewerAuth`.  Uses the viewer token (SHA-256 hashed) as the
  bucket key.  On denial, halts the field resolution with a normalized
  `RATE_LIMITED` error and a `retry_after` extension so clients can back off.

  Emits `[:chatf1, :rate_limit, :deny]` telemetry on each rejected request.
  """

  @behaviour Absinthe.Middleware

  alias Absinthe.Resolution
  alias ChatF1.RateLimit.Server

  @impl true
  def call(%Resolution{context: %{viewer_token: token}} = resolution, _config)
      when is_binary(token) do
    key = :crypto.hash(:sha256, token) |> Base.encode16(case: :lower)

    case Server.check_and_consume(key) do
      :allow ->
        resolution

      {:deny, {:retry_after_seconds, t}} ->
        error = %{
          message: "Rate limit exceeded",
          extensions: %{code: "RATE_LIMITED", retry_after: t}
        }

        Resolution.put_result(resolution, {:error, error})
    end
  end

  def call(resolution, _config) do
    # No viewer token → let ViewerAuth handle it; don't double-error.
    resolution
  end
end
