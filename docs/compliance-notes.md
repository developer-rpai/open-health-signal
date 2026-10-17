# Compliance notes

These are operating notes, not legal advice.

## Postal address before a live send

`NEWSLETTER_POSTAL_ADDRESS` must be a real postal address before any live send. If it is unset, `dispatch-send` refuses a live dispatch and `python -m inflammon newsletter --send` refuses to call Resend. The email template prints no address line when the variable is empty. The public footer uses `NEXT_PUBLIC_POSTAL_ADDRESS` and omits the line when that is unset. Set both to the same deliverable address (a PO Box is acceptable) before the first real mailing.

## Retention job

`public.purge_personal_data()` deletes unconfirmed subscribers after 30 days, strips IP and confirm tokens from unsubscribed rows, and deletes contact messages after 12 months. Schedule it daily in Supabase after enabling `pg_cron`:

```sql
select cron.schedule(
  'purge-personal-data',
  '15 3 * * *',
  $$select public.purge_personal_data()$$
);
```

## Agreements to file outside the repo

Accept the standard data-processing terms from Cloudflare, Supabase, and Resend, and keep the copies with the operator. That step is not something the repository can do.

## Health Breach Notification Rule

The site is a public dashboard plus a one-way mailing list. It is not a personal health record. Do not add, without a fresh review:

- accounts where a person saves their own medications or conditions
- a personal dashboard of their health data
- imports of health data from another source

Any of those would put the project inside the FTC Health Breach Notification Rule.

Do not add analytics, advertising pixels, or a claim that the site is HIPAA compliant.
