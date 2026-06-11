defmodule Mix.Tasks.ChatF1.GenApiKey do
  @shortdoc "Generate and persist a new f1s_-prefixed API key"

  @moduledoc """
  Generates a new `f1s_`-prefixed API key, stores the SHA-256 hash in Postgres,
  and prints the raw key **once** (it is never retrievable again).

  ## Usage

      mix chat_f1.gen_api_key --scope admin:ingest
      mix chat_f1.gen_api_key --scope admin:dashboard --label "grafana-scraper"
      mix chat_f1.gen_api_key --scope admin:ingest --scope admin:dashboard

  ## Options

  * `--scope` — one or more scopes (repeatable). Supported:
      * `admin:ingest`    — allows `triggerIngest` mutation
      * `admin:dashboard` — allows `/dev/dashboard` and `GET /metrics`
  * `--label` — human-readable label for audit logs (optional)

  ## Output

  ```
  Generated API key (store it securely — shown once only):

    f1s_<64 hex chars>

  Key ID: 42  Label: grafana-scraper  Scopes: admin:dashboard
  ```
  """

  use Mix.Task

  @requirements ["app.start"]

  @impl Mix.Task
  def run(args) do
    {opts, _, _} =
      OptionParser.parse(args,
        strict: [scope: :keep, label: :string],
        aliases: [s: :scope, l: :label]
      )

    scopes = Keyword.get_values(opts, :scope)
    label = Keyword.get(opts, :label, "")

    if scopes == [] do
      Mix.raise("At least one --scope is required. Supported: admin:ingest, admin:dashboard")
    end

    {raw_key, changeset} = ChatF1.Accounts.ApiKey.generate(label, scopes)

    case ChatF1.Repo.insert(changeset) do
      {:ok, key} ->
        Mix.shell().info("""

        Generated API key (store it securely — shown once only):

          #{raw_key}

        Key ID: #{key.id}  Label: #{key.label || "(none)"}  Scopes: #{Enum.join(key.scopes, ", ")}
        """)

      {:error, changeset} ->
        Mix.raise("Failed to insert API key: #{inspect(changeset.errors)}")
    end
  end
end
