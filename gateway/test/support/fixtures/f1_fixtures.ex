defmodule ChatF1.Test.F1Fixtures do
  @moduledoc "Factory helpers for F1 test data."

  alias ChatF1.Formula1.{Constructor, Driver, Race, RaceResult}
  alias ChatF1.Repo

  def constructor_fixture(attrs \\ %{}) do
    {:ok, constructor} =
      %Constructor{}
      |> Constructor.changeset(
        Map.merge(
          %{name: "Test Team #{System.unique_integer([:positive])}", points: 0.0},
          attrs
        )
      )
      |> Repo.insert()

    constructor
  end

  def driver_fixture(attrs \\ %{}) do
    constructor = attrs[:constructor] || constructor_fixture()
    n = System.unique_integer([:positive])
    num = rem(n, 99) + 1
    code = "T#{Integer.to_string(rem(n, 99)) |> String.pad_leading(2, "0")}"

    {:ok, driver} =
      %Driver{}
      |> Driver.changeset(
        Map.merge(
          %{
            code: code,
            number: num,
            full_name: "Test Driver #{n}",
            nationality: "British",
            constructor_id: constructor.id
          },
          Map.drop(attrs, [:constructor])
        )
      )
      |> Repo.insert()

    driver
  end

  def race_fixture(attrs \\ %{}) do
    n = System.unique_integer([:positive])
    round = attrs[:round] || rem(n, 24) + 1

    {:ok, race} =
      %Race{}
      |> Race.changeset(
        Map.merge(
          %{
            season: 2025,
            round: round,
            name: "Test Grand Prix #{round}",
            circuit: "Test Circuit",
            country: "Testland",
            starts_at: DateTime.utc_now() |> DateTime.add(30, :day)
          },
          attrs
        )
      )
      |> Repo.insert()

    race
  end

  def race_result_fixture(attrs \\ %{}) do
    driver = attrs[:driver] || driver_fixture()
    race = attrs[:race] || race_fixture()

    {:ok, result} =
      %RaceResult{}
      |> RaceResult.changeset(
        Map.merge(
          %{
            driver_id: driver.id,
            race_id: race.id,
            grid_position: 1,
            finish_position: 1,
            points: 25.0,
            podium: true
          },
          Map.drop(attrs, [:driver, :race])
        )
      )
      |> Repo.insert()

    result
  end
end
