-- Phase 1 list. Subscribers are the source of truth. Resend only sends mail.
-- Studio uses the views at the bottom. The public site does not query these tables.

create type public.subscriber_status as enum (
  'pending',
  'active',
  'unsubscribed',
  'bounced',
  'complained'
);

create table public.subscribers (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  status public.subscriber_status not null default 'pending',
  consent_at timestamptz,
  consent_ip inet,
  confirm_token_hash text,
  confirm_sent_at timestamptz,
  confirmed_at timestamptz,
  unsubscribed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.issues (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  subject text not null,
  headline text,
  html text not null,
  text_body text not null,
  status text not null default 'draft' check (status in ('draft', 'approved', 'sending', 'sent')),
  approved_at timestamptz,
  approved_by uuid,
  created_at timestamptz not null default now()
);

create table public.sends (
  id uuid primary key default gen_random_uuid(),
  issue_slug text not null,
  subscriber_id uuid not null references public.subscribers (id),
  idempotency_key text not null unique,
  status text not null check (status in ('sent', 'dry_run', 'suppressed', 'failed')),
  provider_id text,
  created_at timestamptz not null default now()
);

create table public.contact_requests (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  organization text,
  role text,
  interest_type text not null check (
    interest_type in (
      'research_collaboration',
      'data_expansion',
      'code_contribution',
      'custom_analysis',
      'media',
      'sponsorship'
    )
  ),
  message text not null,
  link text,
  status text not null default 'new' check (status in ('new', 'read', 'closed')),
  notes text,
  created_at timestamptz not null default now()
);

create table public.owner_allowlist (
  email text primary key
);

create table public.rate_limits (
  bucket text primary key,
  hits integer not null,
  window_start timestamptz not null
);

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger subscribers_touch
before update on public.subscribers
for each row execute function public.touch_updated_at();

create or replace function public.is_owner()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.owner_allowlist
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

revoke all on function public.is_owner() from public, anon;
grant execute on function public.is_owner() to authenticated, service_role;

alter table public.subscribers enable row level security;
alter table public.issues enable row level security;
alter table public.sends enable row level security;
alter table public.contact_requests enable row level security;
alter table public.owner_allowlist enable row level security;
alter table public.rate_limits enable row level security;

-- No policies for anon. Service role bypasses RLS and is what the edge functions use.
-- Authenticated owners can preview and approve issues, and can annotate contact requests in Studio.

create policy issues_owner_select on public.issues
for select to authenticated
using (public.is_owner());

create policy issues_owner_update on public.issues
for update to authenticated
using (public.is_owner())
with check (public.is_owner());

create policy contacts_owner_select on public.contact_requests
for select to authenticated
using (public.is_owner());

create policy contacts_owner_update on public.contact_requests
for update to authenticated
using (public.is_owner())
with check (public.is_owner());

create view public.subscriber_search
with (security_invoker = false) as
select
  id,
  email,
  status,
  consent_at,
  consent_ip::text as consent_ip,
  confirmed_at,
  unsubscribed_at,
  created_at
from public.subscribers;

create view public.subscriber_export
with (security_invoker = false) as
select
  email,
  status,
  consent_at,
  consent_ip::text as consent_ip,
  confirmed_at,
  unsubscribed_at,
  created_at
from public.subscribers;

create view public.suppression_list
with (security_invoker = false) as
select id, email, status, unsubscribed_at, updated_at
from public.subscribers
where status in ('unsubscribed', 'bounced', 'complained');

comment on view public.subscriber_search is
  'Supabase Studio: filter subscribers by email or status. The public site does not read this view.';
comment on view public.subscriber_export is
  'Supabase Studio: export the list. Download as CSV from the SQL editor.';
comment on view public.suppression_list is
  'Supabase Studio: addresses that must not be mailed (unsubscribed, bounced, complained).';

revoke all on public.subscriber_search from public, anon, authenticated;
revoke all on public.subscriber_export from public, anon, authenticated;
revoke all on public.suppression_list from public, anon, authenticated;
grant select on public.subscriber_search to postgres, service_role;
grant select on public.subscriber_export to postgres, service_role;
grant select on public.suppression_list to postgres, service_role;
