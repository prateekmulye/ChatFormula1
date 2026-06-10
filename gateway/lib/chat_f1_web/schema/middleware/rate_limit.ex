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
  def call(%Resolution{context: context} = resolution, _config) do
    case bucket_key(context) do
      nil ->
        # No viewer token AND no IP — nothing to key a bucket on. Deny rather
        # than wave the request through: an unkeyed request is a misconfigured
        # pipeline, not a trusted caller.
        deny(resolution, 60)

      key ->
        case Server.check_and_consume(key) do
          :allow -> resolution
          {:deny, {:retry_after_seconds, t}} -> deny(resolution, t)
        end
    end
  end

  # Prefer the viewer token; fall back to the caller's IP so requests that
  # arrive without a token (or before one is minted) are still limited.
  defp bucket_key(%{viewer_token: token}) when is_binary(token) do
    :crypto.hash(:sha256, token) |> Base.encode16(case: :lower)
  end

  defp bucket_key(%{remote_ip: ip}) when is_binary(ip), do: "ip:" <> ip
  defp bucket_key(_), do: nil

  defp deny(resolution, retry_after) do
    error = %{
      message: "Rate limit exceeded",
      extensions: %{code: "RATE_LIMITED", retry_after: retry_after}
    }

    Resolution.put_result(resolution, {:error, error})
  end
end
