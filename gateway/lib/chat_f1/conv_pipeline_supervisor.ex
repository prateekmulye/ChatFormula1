defmodule ChatF1.ConvPipelineSupervisor do
  @moduledoc """
  `:rest_for_one` supervisor grouping the three conversation-pipeline processes.

  Children (in order):

  1. `ChatF1.ConvRegistry` — `Registry` with unique keys.  Via-tuple anchor
     for all `Conversation.Server` lookups.  If the registry crashes, all
     in-flight process lookups fail, so the DynamicSupervisor must also
     restart.  `:rest_for_one` enforces this cascade.

  2. `ChatF1.ConversationSupervisor` — `DynamicSupervisor` that owns one
     `Conversation.Server` per active conversation.

  3. `ChatF1.StreamTaskSupervisor` — `Task.Supervisor` for streaming HTTP
     workers.  Tasks cast events to their owning `Conversation.Server`, so
     they depend on the DynamicSupervisor being alive.

  ## Why not fold these into the root supervisor?

  Keeping them in a dedicated sub-supervisor isolates the failure domain:
  a registry crash cascades only within this sub-tree.  The root supervisor
  (`:one_for_one`) restarts the sub-supervisor as a whole, which re-starts
  the registry and lets the DynamicSupervisor rebuild its children cleanly.
  """

  use Supervisor

  @spec start_link(any()) :: Supervisor.on_start()
  def start_link(init_arg) do
    Supervisor.start_link(__MODULE__, init_arg, name: __MODULE__)
  end

  @impl true
  def init(_init_arg) do
    children = [
      # Registry for per-conversation GenServer lookup via via-tuples.
      {Registry, keys: :unique, name: ChatF1.ConvRegistry},

      # DynamicSupervisor — one child per active conversation.
      {DynamicSupervisor, name: ChatF1.ConversationSupervisor, strategy: :one_for_one},

      # Task.Supervisor — one task per active stream.
      {Task.Supervisor, name: ChatF1.StreamTaskSupervisor}
    ]

    Supervisor.init(children, strategy: :rest_for_one)
  end
end
