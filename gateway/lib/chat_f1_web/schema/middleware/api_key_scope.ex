defmodule ChatF1Web.Schema.Middleware.ApiKeyScope do
  @moduledoc """
  Absinthe middleware that enforces API-key scope on mutations/queries.

  Usage in the schema:

      field :trigger_ingest, :ingest_job do
        middleware ChatF1Web.Schema.Middleware.ApiKeyScope, scope: "admin:ingest"
        resolve &Resolvers.trigger_ingest/3
      end

  Reads `context.api_key` (set by `ChatF1Web.Plugs.ApiKey` → `context/2` in
  `ChatF1Web.Schema`).  Rejects with UNAUTHORIZED if missing or wrong scope.
  """

  @behaviour Absinthe.Middleware

  alias ChatF1.Accounts.ApiKeys

  @impl Absinthe.Middleware
  def call(%Absinthe.Resolution{context: context} = resolution, opts) do
    required_scope = Keyword.get(opts, :scope)
    api_key = Map.get(context, :api_key)

    cond do
      is_nil(required_scope) ->
        # No scope required — just need any valid key.
        if is_nil(api_key) do
          Absinthe.Resolution.put_result(
            resolution,
            {:error, %{message: "API key required", extensions: %{code: "UNAUTHORIZED"}}}
          )
        else
          resolution
        end

      is_nil(api_key) ->
        Absinthe.Resolution.put_result(
          resolution,
          {:error, %{message: "API key required", extensions: %{code: "UNAUTHORIZED"}}}
        )

      not ApiKeys.has_scope?(api_key, required_scope) ->
        Absinthe.Resolution.put_result(
          resolution,
          {:error,
           %{
             message: "Insufficient scope — required: #{required_scope}",
             extensions: %{code: "UNAUTHORIZED"}
           }}
        )

      true ->
        resolution
    end
  end
end
