defmodule ChatF1Web.Schema.Middleware.ViewerAuth do
  @moduledoc """
  Absinthe middleware: asserts a valid viewer is present in the context.

  The `ChatF1Web.Plugs.ViewerToken` plug always assigns a `viewer_id` —
  even first-time visitors get one.  This middleware simply verifies the
  assignment exists so that downstream resolvers can trust `context.viewer_id`.

  If somehow the plug is bypassed (e.g., direct `Absinthe.run/3` in tests),
  this middleware halts with an `:internal` error rather than allowing
  resolvers to run unauthenticated.
  """

  @behaviour Absinthe.Middleware

  alias Absinthe.Resolution

  @impl true
  def call(%Resolution{context: %{viewer_id: id}} = resolution, _config)
      when is_binary(id) and byte_size(id) > 0 do
    resolution
  end

  def call(resolution, _config) do
    Resolution.put_result(resolution, {:error, %{code: :internal, message: "No viewer context"}})
  end
end
