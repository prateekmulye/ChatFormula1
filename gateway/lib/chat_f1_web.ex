defmodule ChatF1Web do
  @moduledoc """
  Entry point for the ChatF1 web layer.

  This module defines helpers that are imported into controllers, views, and
  channels — the standard Phoenix `use` delegation pattern.

  It is intentionally thin: the application is API-only (no HTML, no LiveView,
  no mailer), so only `:controller` and `:router` helpers are defined.
  """

  def static_paths, do: ~w(robots.txt favicon.ico)

  def router do
    quote do
      use Phoenix.Router, helpers: false

      import Plug.Conn
      import Phoenix.Controller
    end
  end

  def controller do
    quote do
      use Phoenix.Controller, formats: [:json]
      import Plug.Conn
    end
  end

  defmacro __using__(which) when is_atom(which) do
    apply(__MODULE__, which, [])
  end
end
