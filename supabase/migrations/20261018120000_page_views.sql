-- Anonymous page views. No IP address, user agent, or name.
-- The public site inserts through the pageview edge function (service role).
-- Studio can read public.page_views_daily. anon and authenticated cannot.

create table public.page_views (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  path text not null check (char_length(path) between 1 and 200 and left(path, 1) = '/'),
  referrer_host text check (referrer_host is null or char_length(referrer_host) <= 253),
  local_time text check (local_time is null or char_length(local_time) <= 32),
  tz text check (tz is null or char_length(tz) <= 64),
  country text check (country is null or country ~ '^[A-Z]{2}$'),
  device_type text not null check (device_type in ('mobile', 'tablet', 'desktop')),
  browser text check (browser is null or char_length(browser) <= 32),
  os text check (os is null or char_length(os) <= 32),
  screen_w integer check (screen_w is null or (screen_w >= 0 and screen_w <= 10000)),
  lang text check (lang is null or char_length(lang) <= 35),
  utm_source text check (utm_source is null or char_length(utm_source) <= 80),
  utm_medium text check (utm_medium is null or char_length(utm_medium) <= 80),
  utm_campaign text check (utm_campaign is null or char_length(utm_campaign) <= 80),
  session_id text not null check (char_length(session_id) between 16 and 64)
);

create index page_views_created_at_idx on public.page_views (created_at);

alter table public.page_views enable row level security;

revoke all on table public.page_views from public, anon, authenticated;
grant select, insert on table public.page_views to service_role;

-- Views per page, per country, per Pacific day.
create view public.page_views_daily
with (security_invoker = false) as
select
  (created_at at time zone 'America/Los_Angeles')::date as day,
  path,
  country,
  count(*)::bigint as views
from public.page_views
group by 1, 2, 3;

comment on view public.page_views_daily is
  'Daily page-view summary in America/Los_Angeles: views per page, per country, per day. The public site does not read this view.';

revoke all on public.page_views_daily from public, anon, authenticated;
grant select on public.page_views_daily to postgres, service_role;
