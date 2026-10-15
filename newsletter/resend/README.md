# Resend alternative

The dashboard is a static export, so it cannot keep a subscriber list itself. Buttondown is the default: the form posts straight to Buttondown, and Buttondown sends the confirmation email.

Use this folder when you want Resend instead. It is a separate deploy, not part of `web/`.

## What it does

1. `POST /subscribe` checks the consent field, then emails a confirmation link.
2. `GET /confirm` checks an HMAC of the address and adds the contact to a Resend audience.
3. The Monday job sends the briefing with `POST /broadcasts` and `POST /broadcasts/{id}/send`. Unsubscribe uses Resend’s `{{{RESEND_UNSUBSCRIBE_URL}}}`.

## Keys

| Variable | Where it lives | What it is |
| --- | --- | --- |
| `RESEND_API_KEY` | This function, and the refresh job if it sends | Resend API key. Secret. |
| `RESEND_AUDIENCE_ID` | This function and the refresh job | Audience that receives the broadcast. |
| `NEWSLETTER_FROM` | This function and the refresh job | Verified sender, for example `Inflammation Signal Monitor <briefing@example.com>`. |
| `NEWSLETTER_CONFIRM_SECRET` | This function only | Long random string used to sign confirmation links. |
| `SUBSCRIBE_FUNCTION_URL` | This function | Public origin of this deploy, with no trailing path. |
| `NEXT_PUBLIC_NEWSLETTER_PROVIDER` | Static site build | Set to `resend`. |
| `NEXT_PUBLIC_SUBSCRIBE_ENDPOINT` | Static site build | Public URL of `POST /subscribe`, for example `https://subscribe.example.com/subscribe`. |
| `NEWSLETTER_PROVIDER` | Refresh job | Set to `resend` so the Monday send uses the broadcast API. |

`RESEND_API_KEY` never belongs in a `NEXT_PUBLIC_` variable. The static site only needs the subscribe URL.

## Deploy

Create a second Vercel project with **Root Directory** `newsletter/resend`. The `api/subscribe.py` and `api/confirm.py` files are the two routes. Set the variables above, then set the static site’s `NEXT_PUBLIC_SUBSCRIBE_ENDPOINT` to the subscribe URL and rebuild the dashboard.

Any other Python host can call `handle_subscribe` and `handle_confirm` in `handler.py`. Those functions take a `post` callable so tests never touch the network.
