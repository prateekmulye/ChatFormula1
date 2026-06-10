defmodule ChatF1Web.Schema.F1QueriesTest do
  @moduledoc """
  GraphQL resolver tests for the F1 structured data surface.
  Uses Absinthe.run/3 directly to test the schema contract.
  """

  use ChatF1.DataCase, async: true

  alias ChatF1.Test.F1Fixtures

  defp run_query(query, viewer_id \\ nil) do
    viewer_id = viewer_id || Ecto.UUID.generate()
    token = ChatF1.Accounts.mint_viewer_token(viewer_id)

    Absinthe.run(query, ChatF1Web.Schema, context: %{viewer_id: viewer_id, viewer_token: token})
    |> case do
      {:ok, result} -> result
      other -> other
    end
  end

  describe "drivers query" do
    test "returns an empty list when no drivers exist" do
      result = run_query("{ drivers { code fullName } }")
      assert result.data["drivers"] == []
    end

    test "returns drivers with expected fields" do
      c = F1Fixtures.constructor_fixture(%{name: "Alpha Team"})
      F1Fixtures.driver_fixture(%{code: "TST", full_name: "Test Driver", constructor: c})

      result = run_query("{ drivers { code fullName constructor { name } } }")
      assert Map.get(result, :errors, []) == []

      drivers = result.data["drivers"]
      assert Enum.any?(drivers, fn d -> d["code"] == "TST" end)
    end
  end

  describe "driver query" do
    test "returns a driver by code" do
      c = F1Fixtures.constructor_fixture()
      F1Fixtures.driver_fixture(%{code: "QRS", full_name: "Query Driver", constructor: c})

      result = run_query(~s|{ driver(code: "QRS") { code fullName } }|)
      assert result.data["driver"]["code"] == "QRS"
    end

    test "returns null for unknown code" do
      result = run_query(~s|{ driver(code: "ZZZ") { code } }|)
      assert result.data["driver"] == nil
    end
  end

  describe "races query" do
    test "returns races for the given season" do
      F1Fixtures.race_fixture(%{season: 2025, round: 1})
      F1Fixtures.race_fixture(%{season: 2025, round: 2})

      result = run_query("{ races(season: 2025) { round name } }")
      races = result.data["races"]
      assert length(races) >= 2
      rounds = Enum.map(races, & &1["round"])
      assert rounds == Enum.sort(rounds)
    end
  end

  describe "standings query" do
    test "returns standings in points-descending order" do
      c = F1Fixtures.constructor_fixture()
      d1 = F1Fixtures.driver_fixture(%{constructor: c})
      d2 = F1Fixtures.driver_fixture(%{constructor: c})
      race = F1Fixtures.race_fixture(%{season: 2077, round: 1})

      F1Fixtures.race_result_fixture(%{driver: d1, race: race, points: 25.0, finish_position: 1})
      F1Fixtures.race_result_fixture(%{driver: d2, race: race, points: 18.0, finish_position: 2})

      result =
        run_query("{ standings(season: 2077) { position points wins podiums driver { code } } }")

      assert Map.get(result, :errors, []) == []

      rows = result.data["standings"]
      assert length(rows) == 2
      assert hd(rows)["points"] == 25.0
      assert hd(rows)["position"] == 1
      assert hd(rows)["wins"] == 1
    end
  end
end
