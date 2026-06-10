defmodule ChatF1.Formula1 do
  @moduledoc """
  Context for structured F1 data: drivers, constructors, races, results, and
  the computed standings view.

  All data originates from `data/drivers.json` and `data/races.json` (seeded
  via `priv/repo/seeds.exs`) and is refreshed nightly by the Jolpica/Ergast
  sync job (Phase 5).

  ### N+1 prevention

  The Dataloader Ecto source (see `ChatF1Web.Schema.Dataloader`) batches all
  association lookups (driver→constructor, constructor→drivers,
  race→race_results, driver→race_results) into single queries per batch.  The
  `standings/1` function issues a single aggregating SQL query — never one
  query per driver.
  """

  import Ecto.Query

  alias ChatF1.Formula1.{Constructor, Driver, Race, RaceResult}
  alias ChatF1.Repo

  # ─── Drivers ────────────────────────────────────────────────────────────────

  @spec list_drivers(keyword()) :: [Driver.t()]
  def list_drivers(opts \\ []) do
    season = Keyword.get(opts, :season)

    Driver
    |> maybe_filter_season(season)
    |> order_by([d], d.code)
    |> Repo.all()
  end

  @spec get_driver_by_code(String.t()) :: Driver.t() | nil
  def get_driver_by_code(code) do
    Repo.get_by(Driver, code: code)
  end

  # ─── Constructors ────────────────────────────────────────────────────────────

  @spec list_constructors() :: [Constructor.t()]
  def list_constructors do
    Constructor
    |> order_by([c], c.name)
    |> Repo.all()
  end

  @spec get_constructor!(integer()) :: Constructor.t()
  def get_constructor!(id), do: Repo.get!(Constructor, id)

  # ─── Races ───────────────────────────────────────────────────────────────────

  @spec list_races(integer()) :: [Race.t()]
  def list_races(season) do
    Race
    |> where([r], r.season == ^season)
    |> order_by([r], r.round)
    |> Repo.all()
  end

  @spec next_race() :: Race.t() | nil
  def next_race do
    now = DateTime.utc_now()

    Race
    |> where([r], r.starts_at > ^now)
    |> order_by([r], asc: r.starts_at)
    |> limit(1)
    |> Repo.one()
  end

  # ─── Race results ────────────────────────────────────────────────────────────

  @spec list_results_for_driver(integer(), keyword()) :: [RaceResult.t()]
  def list_results_for_driver(driver_id, opts \\ []) do
    season = Keyword.get(opts, :season)

    RaceResult
    |> where([rr], rr.driver_id == ^driver_id)
    |> maybe_join_race_season(season)
    |> order_by([rr], desc: rr.id)
    |> Repo.all()
  end

  @spec list_results_for_race(integer()) :: [RaceResult.t()]
  def list_results_for_race(race_id) do
    RaceResult
    |> where([rr], rr.race_id == ^race_id)
    |> order_by([rr], asc: rr.finish_position)
    |> Repo.all()
  end

  # ─── Standings ───────────────────────────────────────────────────────────────

  @doc """
  Returns the computed championship standings for a given season.

  This is a **single aggregating SQL query** — provably N+1 free.  Each
  `StandingRow` struct is assembled from the aggregation result with the
  driver record preloaded via a join.

  The `%{position: _, driver: _, points: _, wins: _, podiums: _}` shape
  matches the `StandingRow` GraphQL type defined in the schema.
  """
  @spec standings(integer()) :: [map()]
  def standings(season) do
    RaceResult
    |> join(:inner, [rr], r in Race, on: rr.race_id == r.id and r.season == ^season)
    |> join(:inner, [rr, _r], d in Driver, on: rr.driver_id == d.id)
    |> group_by([rr, _r, d], d.id)
    |> select([rr, _r, d], %{
      driver: d,
      points: sum(rr.points),
      wins: sum(fragment("CASE WHEN ? = 1 THEN 1 ELSE 0 END", rr.finish_position)),
      podiums: sum(fragment("CASE WHEN ? <= 3 THEN 1 ELSE 0 END", rr.finish_position))
    })
    |> order_by([rr, _r, _d], desc: sum(rr.points))
    |> Repo.all()
    |> Enum.with_index(1)
    |> Enum.map(fn {row, idx} -> Map.put(row, :position, idx) end)
  end

  # ─── Dataloader batch loaders (called by ChatF1Web.Schema.Dataloader) ────────

  @doc """
  Batch-loads constructors for a list of constructor IDs.
  Called by the Dataloader source — never called per-driver.
  """
  @spec constructors_by_ids([integer()]) :: map()
  def constructors_by_ids(ids) do
    Constructor
    |> where([c], c.id in ^ids)
    |> Repo.all()
    |> Map.new(&{&1.id, &1})
  end

  @doc """
  Batch-loads drivers for a list of constructor IDs.
  Returns a map of constructor_id → [%Driver{}].
  """
  @spec drivers_by_constructor_ids([integer()]) :: map()
  def drivers_by_constructor_ids(ids) do
    Driver
    |> where([d], d.constructor_id in ^ids)
    |> Repo.all()
    |> Enum.group_by(& &1.constructor_id)
  end

  @doc """
  Batch-loads race_results for a list of driver IDs.
  Returns a map of driver_id → [%RaceResult{}].
  """
  @spec results_by_driver_ids([integer()], integer() | nil) :: map()
  def results_by_driver_ids(ids, season \\ nil) do
    RaceResult
    |> where([rr], rr.driver_id in ^ids)
    |> maybe_join_race_season(season)
    |> Repo.all()
    |> Enum.group_by(& &1.driver_id)
  end

  @doc """
  Batch-loads race_results for a list of race IDs.
  Returns a map of race_id → [%RaceResult{}].
  """
  @spec results_by_race_ids([integer()]) :: map()
  def results_by_race_ids(ids) do
    RaceResult
    |> where([rr], rr.race_id in ^ids)
    |> order_by([rr], asc: rr.finish_position)
    |> Repo.all()
    |> Enum.group_by(& &1.race_id)
  end

  # ─── Private helpers ─────────────────────────────────────────────────────────

  defp maybe_filter_season(query, nil), do: query

  defp maybe_filter_season(query, season) do
    query
    |> join(:inner, [d], rr in RaceResult, on: rr.driver_id == d.id)
    |> join(:inner, [_d, rr], r in Race, on: rr.race_id == r.id and r.season == ^season)
    |> distinct([d], d.id)
  end

  defp maybe_join_race_season(query, nil), do: query

  defp maybe_join_race_season(query, season) do
    query
    |> join(:inner, [rr], r in Race, on: rr.race_id == r.id and r.season == ^season)
  end
end
