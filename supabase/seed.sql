-- Example rows for a fresh project. Addresses are documentation fixtures, not a real list.

insert into public.owner_allowlist (email)
values ('owner@example.com')
on conflict (email) do nothing;

insert into public.subscribers (id, email, status, consent_at, consent_ip, confirm_token_hash, confirmed_at)
values
  (
    '11111111-1111-4111-8111-111111111111',
    'pending@example.com',
    'pending',
    '2026-10-01T12:00:00Z',
    '203.0.113.10',
    'seed-hash-not-a-real-confirm-token',
    null
  ),
  (
    '22222222-2222-4222-8222-222222222222',
    'active@example.com',
    'active',
    '2026-10-02T12:00:00Z',
    '203.0.113.11',
    null,
    '2026-10-02T12:05:00Z'
  ),
  (
    '33333333-3333-4333-8333-333333333333',
    'unsubscribed@example.com',
    'unsubscribed',
    '2026-10-03T12:00:00Z',
    '203.0.113.12',
    null,
    '2026-10-03T12:05:00Z'
  ),
  (
    '44444444-4444-4444-8444-444444444444',
    'bounced@example.com',
    'bounced',
    '2026-10-04T12:00:00Z',
    '203.0.113.13',
    null,
    '2026-10-04T12:05:00Z'
  ),
  (
    '55555555-5555-4555-8555-555555555555',
    'complained@example.com',
    'complained',
    '2026-10-05T12:00:00Z',
    '203.0.113.14',
    null,
    '2026-10-05T12:05:00Z'
  )
on conflict (email) do nothing;

update public.subscribers
set unsubscribed_at = '2026-10-06T12:00:00Z'
where email = 'unsubscribed@example.com';

insert into public.issues (slug, subject, headline, html, text_body, status)
values (
  '2026-10-15',
  'TNF inhibitors: tuberculosis reported more often than expected (PRR 7.5)',
  'TNF inhibitors: tuberculosis reported more often than expected (PRR 7.5)',
  '<p>Draft preview. The Monday job replaces this HTML with the rendered issue.</p>',
  'Draft preview. The Monday job replaces this text with the rendered issue.',
  'draft'
)
on conflict (slug) do nothing;

insert into public.contact_requests (name, email, organization, role, interest_type, message, link, status, notes)
values (
  'Sample collaborator',
  'lab@example.com',
  'Example Institute',
  'Pharmacoepidemiologist',
  'research_collaboration',
  'Seed row so the contact table is visible in Studio. Notes stay empty until the owner writes them.',
  'https://example.com/lab',
  'new',
  null
);
