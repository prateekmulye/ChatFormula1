defmodule ChatF1Web.Schema.Resolvers.F1Resolvers do
  @moduledoc "Resolver functions for the F1 structured data queries."

  alias ChatF1.Formula1

  # ── Queries ─────────────────────────────────────────────────────────────────

  @doc "Resolves the `drivers` query."
  def list_drivers(_parent, args, _context) do
    drivers = Formula1.list_drivers(season: args[:season])
    {:ok, drivers}
  end

  @doc "Resolves the `driver` query."
  def get_driver(_parent, %{code: code}, _context) do
    {:ok, Formula1.get_driver_by_code(code)}
  end

  @doc "Resolves the `races` query."
  def list_races(_parent, %{season: season}, _context) do
    {:ok, Formula1.list_races(season)}
  end

  @doc "Resolves the `nextRace` query."
  def next_race(_parent, _args, _context) do
    {:ok, Formula1.next_race()}
  end

  @doc "Resolves the `standings` query."
  def standings(_parent, %{season: season}, _context) do
    {:ok, Formula1.standings(season)}
  end
end
