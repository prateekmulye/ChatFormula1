defmodule ChatF1Web.Schema.DataloaderSource do
  @moduledoc """
  Dataloader source wiring for the ChatF1 Ecto repo.

  Loaded associations resolve via batch functions on the context module,
  eliminating N+1 queries.  The Dataloader Ecto source automatically batches
  `Repo.get/2` and simple association loads; we override batch functions for
  more complex associations.

  ### Provable N+1 elimination

  * `Driver.constructor` — batched: one query loads all constructors for all
    drivers in the current resolution batch.
  * `Constructor.drivers` — batched: one query loads all drivers grouped by
    `constructor_id`.
  * `Driver.results` — batched: one query loads all results for all drivers.
  * `Race.results` — batched: one query loads all results for all races.

  None of these trigger per-row queries; the batch size is the entire
  Absinthe resolution batch (typically an entire query's worth of objects).
  """

  alias ChatF1.Repo

  @doc "Returns a Dataloader source configured for ChatF1 context functions."
  def data do
    Dataloader.Ecto.new(Repo, query: &query/2)
  end

  # Default query for Ecto source — passes through as-is.
  # Specific associations are handled via batch callbacks in resolvers.
  defp query(queryable, _params), do: queryable
end
