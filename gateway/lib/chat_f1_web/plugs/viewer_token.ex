defmodule ChatF1Web.Plugs.ViewerToken do
  @moduledoc """
  Extracts or mints an anonymous viewer token from the request.

  ## Token sources (in priority order)

  1. `Authorization: Bearer <token>` header — for Apollo clients sending the
     token as a header after the initial page load.
  2. `_chat_f1_viewer` cookie — set on first visit; survives browser restarts.
  3. None found → mint a new viewer_id, set the cookie, assign to conn.

  The verified `viewer_id` is stored in `conn.assigns.viewer_id`.
  The raw `viewer_token` is stored in `conn.assigns.viewer_token` so the
  response can echo it back for clients that need to persist it.

  ## Security notes

  * Invalid or expired tokens mint a fresh viewer — this is intentional.
    An anonymous viewer losing their token starts a clean session, not an error.
  * The raw token is never logged; only the viewer_id (opaque UUID) appears in
    application logs.
  * HTTPS in production ensures the cookie is not transmitted in cleartext.
  """

  @behaviour Plug

  import Plug.Conn

  alias ChatF1.Accounts

  @cookie_name "_chat_f1_viewer"
  @cookie_max_age 30 * 24 * 60 * 60

  @impl Plug
  def init(opts), do: opts

  @impl Plug
  def call(conn, _opts) do
    {viewer_id, token, fresh?} = resolve_viewer(conn)

    conn =
      conn
      |> assign(:viewer_id, viewer_id)
      |> assign(:viewer_token, token)

    if fresh? do
      put_resp_cookie(conn, @cookie_name, token,
        max_age: @cookie_max_age,
        http_only: true,
        same_site: "Lax"
      )
    else
      conn
    end
  end

  # Try Authorization header first, then cookie, then mint fresh.
  defp resolve_viewer(conn) do
    with {:header, nil} <- {:header, bearer_token(conn)},
         {:cookie, nil} <- {:cookie, cookie_token(conn)} do
      id = Accounts.new_viewer_id()
      token = Accounts.mint_viewer_token(id)
      {id, token, true}
    else
      {:header, token} -> verify_or_mint(token)
      {:cookie, token} -> verify_or_mint(token)
    end
  end

  defp bearer_token(conn) do
    case get_req_header(conn, "authorization") do
      ["Bearer " <> token] -> token
      _ -> nil
    end
  end

  defp cookie_token(conn) do
    conn = fetch_cookies(conn)
    conn.cookies[@cookie_name]
  end

  defp verify_or_mint(token) do
    case Accounts.verify_viewer_token(token) do
      {:ok, viewer_id} ->
        {viewer_id, token, false}

      {:error, _} ->
        id = Accounts.new_viewer_id()
        new_token = Accounts.mint_viewer_token(id)
        {id, new_token, true}
    end
  end
end
