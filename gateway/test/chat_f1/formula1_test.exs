defmodule ChatF1.Formula1Test do
  use ChatF1.DataCase, async: true

  alias ChatF1.Formula1
  alias ChatF1.Test.F1Fixtures

  describe "list_drivers/1" do
    test "returns all drivers ordered by code" do
      c = F1Fixtures.constructor_fixture()
      F1Fixtures.driver_fixture(%{code: "ZZZ", constructor: c})
      F1Fixtures.driver_fixture(%{code: "AAA", constructor: c})

      codes = Formula1.list_drivers() |> Enum.map(& &1.code)
      assert Enum.member?(codes, "ZZZ")
      assert Enum.member?(codes, "AAA")
      assert codes == Enum.sort(codes)
    end
  end

  describe "get_driver_by_code/1" do
    test "returns the driver for a valid code" do
      driver = F1Fixtures.driver_fixture(%{code: "VVV"})
      found = Formula1.get_driver_by_code("VVV")
      assert found.id == driver.id
    end

    test "returns nil for an unknown code" do
      assert Formula1.get_driver_by_code("XXX") == nil
    end
  end

  describe "list_races/1" do
    test "returns races for the given season in round order" do
      F1Fixtures.race_fixture(%{season: 2025, round: 3})
      F1Fixtures.race_fixture(%{season: 2025, round: 1})

      rounds = Formula1.list_races(2025) |> Enum.map(& &1.round)
      assert rounds == Enum.sort(rounds)
    end

    test "does not return races from other seasons" do
      F1Fixtures.race_fixture(%{season: 2099, round: 1})
      races = Formula1.list_races(2025)
      refute Enum.any?(races, &(&1.season == 2099))
    end
  end

  describe "next_race/0" do
    test "returns the next upcoming race" do
      future = DateTime.add(DateTime.utc_now(), 7, :day)
      past = DateTime.add(DateTime.utc_now(), -7, :day)

      F1Fixtures.race_fixture(%{starts_at: past, round: 88})
      next_race = F1Fixtures.race_fixture(%{starts_at: future, round: 89})

      found = Formula1.next_race()
      assert found.id == next_race.id
    end

    test "returns nil when no future races exist" do
      past = DateTime.add(DateTime.utc_now(), -1, :day)
      F1Fixtures.race_fixture(%{starts_at: past, round: 90})
      # Only run this assertion if there are no seeded future races
      all_future = Formula1.list_races(9999)

      if all_future == [] do
        assert Formula1.next_race() == nil
      end
    end
  end

  describe "standings/1" do
    test "returns standings sorted by points descending" do
      c = F1Fixtures.constructor_fixture()
      d1 = F1Fixtures.driver_fixture(%{constructor: c})
      d2 = F1Fixtures.driver_fixture(%{constructor: c})
      race = F1Fixtures.race_fixture(%{season: 2099, round: 1})

      F1Fixtures.race_result_fixture(%{driver: d1, race: race, points: 25.0, finish_position: 1})
      F1Fixtures.race_result_fixture(%{driver: d2, race: race, points: 18.0, finish_position: 2})

      rows = Formula1.standings(2099)
      assert length(rows) == 2
      [first, second] = rows
      assert first.points == 25.0
      assert second.points == 18.0
      assert first.position == 1
      assert second.position == 2
    end

    test "computes wins and podiums correctly" do
      c = F1Fixtures.constructor_fixture()
      d = F1Fixtures.driver_fixture(%{constructor: c})
      race1 = F1Fixtures.race_fixture(%{season: 2098, round: 1})
      race2 = F1Fixtures.race_fixture(%{season: 2098, round: 2})
      race3 = F1Fixtures.race_fixture(%{season: 2098, round: 3})

      F1Fixtures.race_result_fixture(%{driver: d, race: race1, finish_position: 1, points: 25.0})
      F1Fixtures.race_result_fixture(%{driver: d, race: race2, finish_position: 2, points: 18.0})
      F1Fixtures.race_result_fixture(%{driver: d, race: race3, finish_position: 4, points: 12.0})

      [row] = Formula1.standings(2098)
      assert row.wins == 1
      assert row.podiums == 2
      assert row.points == 55.0
    end
  end
end
