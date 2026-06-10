defmodule ChatF1Web.ErrorJSON do
  @moduledoc "JSON error rendering for non-GraphQL routes."

  def render("404.json", _assigns) do
    %{errors: %{detail: "Not Found"}}
  end

  def render("500.json", _assigns) do
    %{errors: %{detail: "Internal Server Error"}}
  end
end
