# Retired

Buttondown, and this Resend audience helper, are not the list. Subscribers live in Supabase Postgres. Resend only sends mail. The HTTP routes are the edge functions in `supabase/functions/`:

- `subscribe` creates a pending row and sends the confirmation email
- `confirm` activates the row
- `unsubscribe` checks an HMAC token; GET asks, POST is RFC 8058 one-click
- `resend-webhook` verifies the Svix signature and suppresses bounces and complaints
- `contact` stores a collaboration message
- `dispatch-send` asks GitHub Actions to send after the owner approves

`handler.py` remains only so an old deploy is obvious in the diff. Do not point the site at it.
