defmodule ChatF1.Repo.Migrations.InstallOban do
  use Ecto.Migration

  def up do
    Oban.Migrations.up(version: 14)
  end

  def down do
    Oban.Migrations.down(version: 1)
  end
end
