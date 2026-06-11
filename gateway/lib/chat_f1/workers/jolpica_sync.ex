defmodule ChatF1.Workers.JolpicaSync do
  @moduledoc """
  Oban worker: nightly sync of F1 drivers, constructors, races, results, and
  standings from the free Jolpica/Ergast API (https://api.jolpi.ca/ergast/f1/).

  ## Schedule

  Runs nightly at 02:00 UTC (configured in `config/runtime.exs`).

  ## Idempotency

  * Scheduled as a unique Oban job (unique by `[queue, worker]` with a 23-hour
    uniqueness window) — only one sync runs per day even if triggered manually.
  * All upserts use `on_conflict: {:replace, [...]}` keyed on natural keys
    (season+round for races, code for drivers, name for constructors).

  ## Failure semantics

  * Exponential backoff: Oban defaults (10 attempts, `attempt^4` seconds).
  * After all attempts exhausted the job is marked `:discarded`; the last-synced
    timestamp in `systemStats` remains stale — surfaced honestly to the UI.

  ## Jolpica API shape

  `GET https://api.jolpi.ca/ergast/f1/<year>/driverStandings.json`
  `GET https://api.jolpi.ca/ergast/f1/<year>/constructorStandings.json`
  `GET https://api.jolpi.ca/ergast/f1/<year>/results.json?limit=1000`

  The API is a community-maintained fork of the Ergast Developer API.
  It returns the Ergast JSON envelope shape unchanged.
  """

  use Oban.Worker,
    queue: :default,
    unique: [period: 23 * 60 * 60],
    max_attempts: 10

  require Logger

  alias ChatF1.Formula1
  alias ChatF1.Repo

  @jolpica_base "https://api.jolpi.ca/ergast/f1"
  @current_season 2025
  @recv_timeout 30_000

  @impl Oban.Worker
  def perform(%Oban.Job{args: args}) do
    season = Map.get(args, "season", @current_season)

    Logger.info("[JolpicaSync] starting sync for season #{season}")

    with {:ok, _} <- sync_constructors(season),
         {:ok, _} <- sync_drivers(season),
         {:ok, _} <- sync_races(season),
         {:ok, _} <- sync_results(season),
         {:ok, _} <- sync_standings(season) do
      # Persist last-synced timestamp via ETS (read by systemStats telemetry).
      :ets.insert(:chatf1_stats, {:last_standings_sync_at, DateTime.utc_now()})
      Logger.info("[JolpicaSync] season #{season} sync complete")
      :ok
    else
      {:error, reason} ->
        Logger.error("[JolpicaSync] sync failed: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # ─── Constructors ─────────────────────────────────────────────────────────────

  defp sync_constructors(season) do
    url = "#{@jolpica_base}/#{season}/constructorStandings.json"

    case get_json(url) do
      {:ok, body} ->
        standings =
          get_in(body, [
            "MRData",
            "StandingsTable",
            "StandingsLists",
            Access.at(0),
            "ConstructorStandings"
          ]) || []

        Repo.transaction(fn ->
          Enum.each(standings, fn row ->
            constructor = row["Constructor"]
            points = parse_float(row["points"])

            Formula1.upsert_constructor(%{
              name: constructor["constructorId"],
              points: points
            })
          end)
        end)

      {:error, _} = err ->
        err
    end
  end

  # ─── Drivers ──────────────────────────────────────────────────────────────────

  defp sync_drivers(season) do
    url = "#{@jolpica_base}/#{season}/driverStandings.json"

    case get_json(url) do
      {:ok, body} ->
        standings =
          get_in(body, [
            "MRData",
            "StandingsTable",
            "StandingsLists",
            Access.at(0),
            "DriverStandings"
          ]) || []

        Repo.transaction(fn ->
          Enum.each(standings, fn row ->
            driver = row["Driver"]
            constructor_name = get_in(row, ["Constructors", Access.at(0), "constructorId"])

            Formula1.upsert_driver(%{
              code: driver["code"] || String.upcase(String.slice(driver["driverId"], 0..2)),
              full_name: "#{driver["givenName"]} #{driver["familyName"]}",
              number: parse_int(driver["permanentNumber"]),
              nationality: driver["nationality"],
              constructor_name: constructor_name
            })
          end)
        end)

      {:error, _} = err ->
        err
    end
  end

  # ─── Races ────────────────────────────────────────────────────────────────────

  defp sync_races(season) do
    url = "#{@jolpica_base}/#{season}.json"

    case get_json(url) do
      {:ok, body} ->
        races = get_in(body, ["MRData", "RaceTable", "Races"]) || []

        Repo.transaction(fn ->
          Enum.each(races, fn race ->
            {:ok, starts_at} = parse_race_datetime(race)

            Formula1.upsert_race(%{
              season: season,
              round: parse_int(race["round"]),
              name: race["raceName"],
              circuit: get_in(race, ["Circuit", "circuitName"]) || "",
              country: get_in(race, ["Circuit", "Location", "country"]) || "",
              starts_at: starts_at
            })
          end)
        end)

      {:error, _} = err ->
        err
    end
  end

  # ─── Results ──────────────────────────────────────────────────────────────────

  defp sync_results(season) do
    url = "#{@jolpica_base}/#{season}/results.json?limit=1000"

    case get_json(url) do
      {:ok, body} ->
        races = get_in(body, ["MRData", "RaceTable", "Races"]) || []

        Repo.transaction(fn ->
          Enum.each(races, fn race ->
            round = parse_int(race["round"])

            Enum.each(race["Results"] || [], fn result ->
              driver_code =
                result["Driver"]["code"] ||
                  String.upcase(String.slice(result["Driver"]["driverId"], 0..2))

              finish_pos = parse_int(result["position"])
              grid_pos = parse_int(result["grid"])
              points = parse_float(result["points"])

              Formula1.upsert_race_result(%{
                season: season,
                round: round,
                driver_code: driver_code,
                finish_position: finish_pos,
                grid_position: grid_pos,
                points: points
              })
            end)
          end)
        end)

      {:error, _} = err ->
        err
    end
  end

  # ─── Standings (just updates constructor + driver points) ────────────────────

  defp sync_standings(_season), do: {:ok, :skipped}

  # ─── HTTP helper ──────────────────────────────────────────────────────────────

  defp get_json(url) do
    Logger.debug("[JolpicaSync] GET #{url}")

    case Req.get(url, receive_timeout: @recv_timeout, headers: [{"accept", "application/json"}]) do
      {:ok, %Req.Response{status: 200, body: body}} when is_map(body) ->
        {:ok, body}

      {:ok, %Req.Response{status: 200, body: body}} when is_binary(body) ->
        case Jason.decode(body) do
          {:ok, decoded} -> {:ok, decoded}
          {:error, e} -> {:error, {:json_parse, e}}
        end

      {:ok, %Req.Response{status: status}} ->
        {:error, {:http_status, status}}

      {:error, exception} ->
        {:error, {:transport, Exception.message(exception)}}
    end
  end

  # ─── Parsing helpers ──────────────────────────────────────────────────────────

  defp parse_float(nil), do: 0.0
  defp parse_float(s) when is_binary(s), do: Float.parse(s) |> elem(0)
  defp parse_float(n) when is_number(n), do: n / 1

  defp parse_int(nil), do: nil
  defp parse_int(s) when is_binary(s), do: Integer.parse(s) |> elem(0)
  defp parse_int(n) when is_integer(n), do: n

  defp parse_race_datetime(%{"date" => date, "time" => time}) do
    with {:ok, naive} <- NaiveDateTime.from_iso8601("#{date}T#{time}"),
         {:ok, dt} <- DateTime.from_naive(naive, "Etc/UTC") do
      {:ok, dt}
    end
  end

  defp parse_race_datetime(%{"date" => date}) do
    {:ok, d} = Date.from_iso8601(date)
    {:ok, DateTime.new!(d, ~T[12:00:00], "Etc/UTC")}
  end
end
