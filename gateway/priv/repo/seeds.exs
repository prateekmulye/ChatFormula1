# Seeds for ChatFormula1 Phase 2.
#
# Loads drivers and races from ../../data/*.json, derives constructors from
# driver records, and inserts everything idempotently using upserts.
#
# Run with:   mix run priv/repo/seeds.exs
# Reset with: mix ecto.reset

alias ChatF1.{Formula1, Repo}
alias ChatF1.Formula1.{Constructor, Driver, Race}

import Ecto.Query

# ─── Paths ────────────────────────────────────────────────────────────────────

data_dir = Path.join([__DIR__, "..", "..", "..", "data"])
drivers_path = Path.join(data_dir, "drivers.json")
races_path = Path.join(data_dir, "races.json")

# ─── Load source data ─────────────────────────────────────────────────────────

drivers_raw = drivers_path |> File.read!() |> Jason.decode!()
races_raw = races_path |> File.read!() |> Jason.decode!()

# ─── Constructors ─────────────────────────────────────────────────────────────
# Derive unique constructors from driver records.
# One driver row per constructor is enough to determine points.

constructor_data =
  drivers_raw
  |> Enum.uniq_by(& &1["constructor"])
  |> Enum.map(fn d ->
    %{name: d["constructor"], points: d["constructorPoints"] || 0.0, nationality: nil}
  end)

IO.puts("Seeding #{length(constructor_data)} constructors...")

constructor_ids =
  Enum.reduce(constructor_data, %{}, fn attrs, acc ->
    result =
      Repo.insert!(
        %Constructor{}
        |> Constructor.changeset(attrs),
        on_conflict: {:replace, [:points, :updated_at]},
        conflict_target: :name,
        returning: true
      )

    Map.put(acc, attrs.name, result.id)
  end)

# ─── Drivers ──────────────────────────────────────────────────────────────────

IO.puts("Seeding #{length(drivers_raw)} drivers...")

Enum.each(drivers_raw, fn d ->
  constructor_id = Map.fetch!(constructor_ids, d["constructor"])

  Repo.insert!(
    %Driver{}
    |> Driver.changeset(%{
      code: d["code"],
      number: d["number"],
      full_name: d["name"],
      nationality: d["nationality"],
      constructor_id: constructor_id
    }),
    on_conflict: {:replace, [:number, :full_name, :nationality, :constructor_id, :updated_at]},
    conflict_target: :code
  )
end)

# ─── Races ────────────────────────────────────────────────────────────────────

IO.puts("Seeding #{length(races_raw)} races...")

Enum.each(races_raw, fn r ->
  # Parse the date string into a UTC datetime (races start at noon UTC as a
  # seed-time approximation; the nightly Jolpica sync fills in exact times).
  {:ok, date} = Date.from_iso8601(r["date"])
  starts_at = DateTime.new!(date, ~T[12:00:00], "Etc/UTC")

  Repo.insert!(
    %Race{}
    |> Race.changeset(%{
      season: r["season"],
      round: r["round"],
      name: r["name"],
      circuit: r["circuit"],
      country: r["country"],
      starts_at: starts_at
    }),
    on_conflict: {:replace, [:name, :circuit, :country, :starts_at, :updated_at]},
    conflict_target: [:season, :round]
  )
end)

IO.puts("Seeds complete.")
IO.puts("  Constructors: #{Repo.aggregate(Constructor, :count)}")
IO.puts("  Drivers:      #{Repo.aggregate(Driver, :count)}")
IO.puts("  Races:        #{Repo.aggregate(Race, :count)}")
