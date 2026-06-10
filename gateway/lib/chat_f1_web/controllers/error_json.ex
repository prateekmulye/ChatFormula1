defmodule ChatF1Web.ErrorJSON do
  @moduledoc "JSON error rendering for non-GraphQL routes."

  # Renders any "<status>.json" template ("404.json", "406.json", ...) from
  # the standard Plug status message, so unexpected statuses never crash the
  # error renderer itself.
  def render(template, _assigns) do
    %{errors: %{detail: Phoenix.Controller.status_message_from_template(template)}}
  end
end
