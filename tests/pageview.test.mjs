import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  allowedPageViewOrigin,
  buildPageView,
  handlePageView,
  normalizePageView,
  pacificDay,
  referrerHost,
  resolveCountry,
  shouldTrack,
  summarizePageViews,
  tabSessionId,
} from "../supabase/functions/_shared/pageview.js";

const SESSION = "11111111-1111-4111-8111-111111111111";
const CHROME_MAC =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36";

test("page-view origins are the public site and pages.dev", () => {
  assert.equal(allowedPageViewOrigin("https://openhealthsignals.org"), true);
  assert.equal(allowedPageViewOrigin("https://www.openhealthsignals.org"), true);
  assert.equal(allowedPageViewOrigin("https://open-health-signals.pages.dev"), true);
  assert.equal(allowedPageViewOrigin("https://preview.foo.pages.dev"), true);
  assert.equal(allowedPageViewOrigin("https://pages.dev"), false);
  assert.equal(allowedPageViewOrigin("https://evilpages.dev"), false);
  assert.equal(allowedPageViewOrigin("https://openhealthsignals.org.evil.example"), false);
  assert.equal(allowedPageViewOrigin("http://openhealthsignals.org"), false);
  assert.equal(allowedPageViewOrigin("https://localhost"), false);
});

test("country prefers cf-ipcountry and falls back to the Intl region", () => {
  assert.equal(resolveCountry("us", "DE"), "US");
  assert.equal(resolveCountry("XX", "de"), "DE");
  assert.equal(resolveCountry("T1", ""), null);
  assert.equal(resolveCountry("", "USA"), null);
});

test("a page view stores the referrer host and drops ip, user agent, and name", () => {
  const normalized = normalizePageView(
    {
      path: "/trends?utm_source=newsletter",
      referrer_host: "https://news.ycombinator.com/item?id=1",
      local_time: "2026-10-17 21:07:00",
      tz: "America/Los_Angeles",
      region: "US",
      device_type: "desktop",
      browser: "Chrome",
      os: "macOS",
      screen_w: 1440,
      lang: "en-US",
      utm_source: "newsletter",
      utm_medium: "email",
      utm_campaign: "oct-18",
      session_id: SESSION,
      ip: "203.0.113.10",
      user_agent: CHROME_MAC,
      name: "Ada Lovelace",
    },
    { countryHeader: "CA", userAgent: CHROME_MAC },
  );
  assert.equal(normalized.ok, true);
  assert.equal(normalized.row.path, "/trends");
  assert.equal(normalized.row.referrer_host, "news.ycombinator.com");
  assert.equal(normalized.row.country, "CA");
  assert.equal(normalized.row.browser, "Chrome");
  assert.equal(normalized.row.os, "macOS");
  assert.equal(normalized.row.utm_source, "newsletter");
  assert.equal("ip" in normalized.row, false);
  assert.equal("user_agent" in normalized.row, false);
  assert.equal("name" in normalized.row, false);
  assert.equal(referrerHost("https://www.google.com/search?q=ra"), "www.google.com");
});

test("tracking skips bots, localhost, Do Not Track, and Global Privacy Control", () => {
  const person = { hostname: "openhealthsignals.org", userAgent: CHROME_MAC, doNotTrack: null, globalPrivacyControl: false };
  assert.equal(shouldTrack(person), true);
  assert.equal(shouldTrack({ ...person, userAgent: "Mozilla/5.0 (compatible; Googlebot/2.1)" }), false);
  assert.equal(shouldTrack({ ...person, hostname: "localhost" }), false);
  assert.equal(shouldTrack({ ...person, hostname: "127.0.0.1" }), false);
  assert.equal(shouldTrack({ ...person, doNotTrack: "1" }), false);
  assert.equal(shouldTrack({ ...person, globalPrivacyControl: true }), false);
});

test("session id is written to the storage it is given", () => {
  const writes = [];
  const storage = {
    getItem() {
      return null;
    },
    setItem(key, value) {
      writes.push([key, value]);
    },
  };
  const id = tabSessionId(storage, () => SESSION);
  assert.equal(id, SESSION);
  assert.deepEqual(writes, [["ohs_page", SESSION]]);
  const again = tabSessionId(
    {
      getItem(key) {
        assert.equal(key, "ohs_page");
        return SESSION;
      },
      setItem() {
        throw new Error("session id should be reused");
      },
    },
    () => "22222222-2222-4222-8222-222222222222",
  );
  assert.equal(again, SESSION);
});

test("client payload is one page view with utm fields and no click stream", () => {
  const payload = buildPageView({
    path: "/methods",
    referrer: "https://example.com/article",
    search: "?utm_source=site&utm_medium=link&utm_campaign=footer",
    localTime: "2026-10-17 21:07:04",
    timeZone: "America/Los_Angeles",
    region: "US",
    userAgent: CHROME_MAC,
    screenWidth: 390,
    language: "en-US",
    maxTouchPoints: 0,
    sessionId: SESSION,
  });
  assert.equal(payload.path, "/methods");
  assert.equal(payload.referrer_host, "example.com");
  assert.equal(payload.device_type, "mobile");
  assert.equal(payload.utm_campaign, "footer");
  assert.equal("click" in payload, false);
  assert.equal("scroll" in payload, false);
});

test("daily summary groups by Pacific day, page, and country", () => {
  assert.equal(pacificDay("2026-10-18T06:30:00Z"), "2026-10-17");
  assert.equal(pacificDay("2026-10-18T07:00:00Z"), "2026-10-18");
  const rows = summarizePageViews([
    { created_at: "2026-10-18T06:30:00Z", path: "/", country: "US" },
    { created_at: "2026-10-18T06:40:00Z", path: "/", country: "US" },
    { created_at: "2026-10-18T07:05:00Z", path: "/", country: "US" },
    { created_at: "2026-10-18T07:06:00Z", path: "/trends", country: "DE" },
  ]);
  assert.deepEqual(rows, [
    { day: "2026-10-17", path: "/", country: "US", views: 2 },
    { day: "2026-10-18", path: "/", country: "US", views: 1 },
    { day: "2026-10-18", path: "/trends", country: "DE", views: 1 },
  ]);
});

test("pageview handler inserts one row and returns 204", async () => {
  const inserted = [];
  const rates = [];
  const deps = {
    serviceClient() {
      return {
        from(table) {
          assert.equal(table, "page_views");
          return {
            insert(row) {
              inserted.push(row);
              return Promise.resolve({ error: null });
            },
          };
        },
      };
    },
    takeRate(_db, bucket) {
      rates.push(bucket);
      return Promise.resolve(true);
    },
  };
  const body = JSON.stringify({
    path: "/signals",
    referrer_host: "https://news.ycombinator.com/item?id=1",
    local_time: "2026-10-17 21:07:00",
    tz: "America/Los_Angeles",
    region: "US",
    device_type: "desktop",
    screen_w: 1280,
    lang: "en-US",
    session_id: SESSION,
    ip: "203.0.113.8",
    name: "Ada",
  });
  const response = await handlePageView(
    new Request("https://example.supabase.co/pageview", {
      method: "POST",
      headers: {
        origin: "https://openhealthsignals.org",
        "content-type": "text/plain;charset=UTF-8",
        "cf-ipcountry": "FR",
        "user-agent": CHROME_MAC,
      },
      body,
    }),
    deps,
  );
  assert.equal(response.status, 204);
  assert.equal(response.headers.get("access-control-allow-origin"), "https://openhealthsignals.org");
  assert.equal(await response.text(), "");
  assert.equal(inserted.length, 1);
  assert.equal(inserted[0].path, "/signals");
  assert.equal(inserted[0].country, "FR");
  assert.equal(inserted[0].referrer_host, "news.ycombinator.com");
  assert.equal("ip" in inserted[0], false);
  assert.equal("user_agent" in inserted[0], false);
  assert.equal("name" in inserted[0], false);
  assert.deepEqual(rates, [`pageview:${SESSION}`]);

  const limited = await handlePageView(
    new Request("https://example.supabase.co/pageview", {
      method: "POST",
      headers: { origin: "https://www.openhealthsignals.org", "content-type": "application/json" },
      body,
    }),
    { ...deps, takeRate: () => Promise.resolve(false) },
  );
  assert.equal(limited.status, 429);
  assert.equal(inserted.length, 1);

  const foreign = await handlePageView(
    new Request("https://example.supabase.co/pageview", {
      method: "POST",
      headers: { origin: "https://evil.example", "content-type": "application/json" },
      body,
    }),
    deps,
  );
  assert.equal(foreign.status, 403);
  assert.equal(foreign.headers.get("access-control-allow-origin"), null);
});

test("migration defines page_views, private RLS, and the Pacific daily view", () => {
  const sql = readFileSync(new URL("../supabase/migrations/20261018120000_page_views.sql", import.meta.url), "utf8");
  for (const column of [
    "created_at timestamptz",
    "path text",
    "referrer_host text",
    "local_time text",
    "tz text",
    "country text",
    "device_type text",
    "browser text",
    "os text",
    "screen_w integer",
    "lang text",
    "utm_source text",
    "utm_medium text",
    "utm_campaign text",
    "session_id text",
  ]) {
    assert.equal(sql.includes(column), true, column);
  }
  assert.equal(sql.includes("enable row level security"), true);
  assert.equal(sql.includes("create policy"), false);
  assert.equal(sql.includes("inet"), false);
  assert.match(sql, /revoke all on table public\.page_views from public, anon, authenticated/);
  assert.match(sql, /create view public\.page_views_daily/);
  assert.match(sql, /America\/Los_Angeles/);
  assert.match(sql, /count\(\*\)::bigint as views/);
  const privacy = readFileSync(new URL("../web/src/app/privacy/page.tsx", import.meta.url), "utf8").replace(/\s+/g, " ");
  assert.match(
    privacy,
    /The site records anonymous page views \(the page, time, country, device type, and referrer\) with no cookies or IP addresses/,
  );
  assert.match(privacy, /NEXT_PUBLIC_CF_BEACON_TOKEN/);
  assert.match(privacy, /and uses Cloudflare Web Analytics/);
});
