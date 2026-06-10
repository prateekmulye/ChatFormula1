defmodule ChatF1Web.Schema.Types.F1Types do
  @moduledoc "Absinthe type definitions for the F1 structured data surface."

  use Absinthe.Schema.Notation
  import Absinthe.Resolution.Helpers, only: [dataloader: 3]

  object :constructor do
    @desc "An F1 constructor (team)."
    field :id, non_null(:id)
    field :name, non_null(:string)
    field :nationality, :string
    field :points, non_null(:float)

    @desc "All drivers belonging to this constructor. Dataloader-batched."
    field :drivers, list_of(non_null(:driver)) do
      resolve(dataloader(ChatF1.Formula1, :drivers, args: %{}))
    end
  end

  object :driver do
    @desc "An F1 driver."
    field :id, non_null(:id)
    field :code, non_null(:string)
    field :number, :integer
    field :full_name, non_null(:string)
    field :nationality, non_null(:string)

    @desc "The driver's constructor (team). Dataloader-batched."
    field :constructor, non_null(:constructor) do
      resolve(dataloader(ChatF1.Formula1, :constructor, args: %{}))
    end

    @desc "Race results, optionally filtered by season. Dataloader-batched."
    field :results, list_of(non_null(:race_result)) do
      arg(:season, :integer)
      resolve(dataloader(ChatF1.Formula1, :race_results, args: %{}))
    end
  end

  object :race do
    @desc "An F1 race event."
    field :id, non_null(:id)
    field :season, non_null(:integer)
    field :round, non_null(:integer)
    field :name, non_null(:string)
    field :circuit, non_null(:string)
    field :country, non_null(:string)
    field :starts_at, non_null(:datetime)

    @desc "Race results in finish order. Dataloader-batched."
    field :results, list_of(non_null(:race_result)) do
      resolve(dataloader(ChatF1.Formula1, :race_results, args: %{}))
    end
  end

  object :race_result do
    @desc "A single driver's result in one race."
    field :id, non_null(:id)
    field :grid_position, :integer
    field :finish_position, :integer
    field :points, non_null(:float)
    field :podium, non_null(:boolean)

    field :driver, non_null(:driver) do
      resolve(dataloader(ChatF1.Formula1, :driver, args: %{}))
    end

    field :race, non_null(:race) do
      resolve(dataloader(ChatF1.Formula1, :race, args: %{}))
    end
  end

  @desc "A row in the championship standings for a given season."
  object :standing_row do
    field :position, non_null(:integer)
    field :driver, non_null(:driver)
    field :points, non_null(:float)
    field :wins, non_null(:integer)
    field :podiums, non_null(:integer)
  end
end
