-- Retention for the mailing list and contact form.
-- Pending confirmations: delete after 30 days.
-- Unsubscribed: keep a suppression record (email, status, unsubscribed_at) and clear the IP and confirm token.
-- Contact messages: delete after 12 months.
--
-- Schedule daily on Supabase once pg_cron is enabled:
--   select cron.schedule(
--     'purge-personal-data',
--     '15 3 * * *',
--     $$select public.purge_personal_data()$$
--   );

create or replace function public.purge_personal_data()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.sends
  where subscriber_id in (
    select id
    from public.subscribers
    where status = 'pending'
      and created_at < now() - interval '30 days'
  );

  delete from public.subscribers
  where status = 'pending'
    and created_at < now() - interval '30 days';

  update public.subscribers
  set consent_ip = null,
      confirm_token_hash = null
  where status = 'unsubscribed'
    and (consent_ip is not null or confirm_token_hash is not null);

  delete from public.contact_requests
  where created_at < now() - interval '12 months';
end;
$$;

revoke all on function public.purge_personal_data() from public, anon, authenticated;
grant execute on function public.purge_personal_data() to service_role;
