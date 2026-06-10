defmodule ChatF1.Repo do
  @moduledoc "Ecto repository backed by PostgreSQL."

  use Ecto.Repo,
    otp_app: :chat_f1,
    adapter: Ecto.Adapters.Postgres
end
