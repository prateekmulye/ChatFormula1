defmodule ChatF1Web.Schema.Middleware.ErrorHandler do
  @moduledoc """
  Absinthe middleware: normalizes errors into the ErrorCode enum shape.

  Applied at the end of every field's middleware stack.  Converts Ecto,
  Changeset, and internal errors into structured `%{message, extensions}` maps
  so the GraphQL response is consistent regardless of the error source.

  ### Error shape contract

  All errors have the shape:
  ```json
  {
    "message": "Human-readable description",
    "extensions": { "code": "ERROR_CODE_ENUM_VALUE" }
  }
  ```

  This mirrors the Apollo Client error handling convention and is enforced
  for every mutation and resolver in the schema.
  """

  @behaviour Absinthe.Middleware

  require Logger

  alias Absinthe.Resolution

  @impl true
  def call(%Resolution{errors: []} = resolution, _config), do: resolution

  def call(%Resolution{errors: errors} = resolution, _config) do
    normalized = Enum.map(errors, &normalize/1)
    %{resolution | errors: normalized}
  end

  # Already normalized (has :message and :extensions keys)
  defp normalize(%{message: _, extensions: _} = error), do: error

  # Atom shorthand → convert to structured error
  defp normalize(:upstream_unavailable) do
    %{message: "Upstream service unavailable", extensions: %{code: "UPSTREAM_UNAVAILABLE"}}
  end

  defp normalize(:not_found) do
    %{message: "Resource not found", extensions: %{code: "NOT_FOUND"}}
  end

  defp normalize(:rate_limited) do
    %{message: "Rate limit exceeded", extensions: %{code: "RATE_LIMITED"}}
  end

  defp normalize(%{code: code, message: message}) when is_atom(code) do
    %{message: message, extensions: %{code: to_string(code) |> String.upcase()}}
  end

  defp normalize(%Ecto.Changeset{} = changeset) do
    message =
      Ecto.Changeset.traverse_errors(changeset, fn {msg, opts} ->
        Regex.replace(~r"%{(\w+)}", msg, fn _, key ->
          opts |> Keyword.get(String.to_existing_atom(key), key) |> to_string()
        end)
      end)
      |> Enum.map_join("; ", fn {field, errors} ->
        "#{field}: #{Enum.join(errors, ", ")}"
      end)

    %{message: message, extensions: %{code: "VALIDATION"}}
  end

  defp normalize(other) do
    # Never echo unrecognized error terms to the client — they can carry
    # internal module names, struct contents, or upstream response bodies.
    Logger.error("Unhandled GraphQL error term: #{inspect(other)}")
    %{message: "Internal server error", extensions: %{code: "INTERNAL"}}
  end
end
