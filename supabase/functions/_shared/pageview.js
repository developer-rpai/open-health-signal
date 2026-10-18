/** Anonymous page-view payload. No IP address, user agent, or name is returned. */

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const BROWSERS = new Set(["Chrome", "Firefox", "Safari", "Edge", "Opera", "Other"]);
const OSES = new Set(["Windows", "macOS", "iOS", "Android", "Linux", "ChromeOS", "Other"]);
const DEVICES = new Set(["mobile", "tablet", "desktop"]);
const UNKNOWN_COUNTRY = new Set(["XX", "T1"]);

export function allowedPageViewOrigin(origin) {
  if (!origin || typeof origin !== "string") return false;
  let url;
  try {
    url = new URL(origin);
  } catch {
    return false;
  }
  if (url.protocol !== "https:") return false;
  if (url.username || url.password) return false;
  const host = url.hostname.toLowerCase();
  if (host === "openhealthsignals.org" || host === "www.openhealthsignals.org") return true;
  return host.endsWith(".pages.dev") && host.length > ".pages.dev".length;
}

export function resolveCountry(headerValue, region) {
  const header = String(headerValue || "").trim().toUpperCase();
  if (/^[A-Z]{2}$/.test(header) && !UNKNOWN_COUNTRY.has(header)) return header;
  const fallback = String(region || "").trim().toUpperCase();
  if (/^[A-Z]{2}$/.test(fallback) && !UNKNOWN_COUNTRY.has(fallback)) return fallback;
  return null;
}

export function referrerHost(value) {
  const raw = String(value || "").trim();
  if (!raw) return null;
  try {
    const withScheme = raw.includes("://") ? raw : `https://${raw}`;
    const host = new URL(withScheme).hostname.toLowerCase().replace(/\.$/, "");
    if (!host || host.length > 253 || !/^[a-z0-9.-]+$/.test(host) || host.includes("..")) return null;
    return host;
  } catch {
    return null;
  }
}

export function pagePath(value) {
  const raw = String(value || "").trim();
  if (!raw.startsWith("/") || raw.startsWith("//")) return null;
  const path = raw.split("?")[0].split("#")[0];
  if (path.length > 200 || /[\s\\]/.test(path)) return null;
  return path;
}

export function browserName(userAgent) {
  const agent = String(userAgent || "");
  if (/edg\//i.test(agent)) return "Edge";
  if (/opr\/|opera/i.test(agent)) return "Opera";
  if (/firefox|fxios/i.test(agent)) return "Firefox";
  if (/chrome|crios|chromium/i.test(agent)) return "Chrome";
  if (/safari/i.test(agent)) return "Safari";
  return "Other";
}

export function osName(userAgent) {
  const agent = String(userAgent || "");
  if (/android/i.test(agent)) return "Android";
  if (/iphone|ipad|ipod/i.test(agent)) return "iOS";
  if (/cros/i.test(agent)) return "ChromeOS";
  if (/windows/i.test(agent)) return "Windows";
  if (/mac os/i.test(agent)) return "macOS";
  if (/linux/i.test(agent)) return "Linux";
  return "Other";
}

export function deviceType({ width, userAgent, maxTouchPoints }) {
  const agent = String(userAgent || "");
  const screen = Number(width) || 0;
  if (/ipad|tablet|playbook|silk/i.test(agent) || /android(?!.*mobile)/i.test(agent)) return "tablet";
  if (/mobi|iphone|ipod|windows phone/i.test(agent)) return "mobile";
  if (Number(maxTouchPoints) > 1 && screen >= 600 && screen < 1024) return "tablet";
  if (screen > 0 && screen < 768) return "mobile";
  return "desktop";
}

export function shouldTrack(input) {
  const source = input || {};
  const hostname = String(source.hostname || "").toLowerCase().replace(/^\[|\]$/g, "");
  if (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "::1" ||
    hostname.endsWith(".localhost") ||
    hostname.endsWith(".local")
  ) {
    return false;
  }
  const agent = String(source.userAgent || "");
  if (/bot|crawler|spider|crawling|slurp|bingpreview|facebookexternalhit|mediapartners|headless|lighthouse|pagespeed|wget|curl|python-requests|httpclient/i.test(agent)) {
    return false;
  }
  const dnt = String(source.doNotTrack ?? "").toLowerCase();
  if (dnt === "1" || dnt === "yes") return false;
  if (source.globalPrivacyControl === true || source.globalPrivacyControl === "1") return false;
  return true;
}

export function tabSessionId(storage, randomUUID) {
  const key = "ohs_page";
  const existing = storage.getItem(key);
  if (existing && UUID.test(existing)) return existing;
  const id = String(randomUUID());
  storage.setItem(key, id);
  return id;
}

export function localWallClock(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function intlRegion(language, locale) {
  const tag = String(language || locale || "");
  try {
    const region = new Intl.Locale(tag).region;
    return region || "";
  } catch {
    const match = tag.match(/[-_]([A-Za-z]{2})\b/);
    return match ? match[1].toUpperCase() : "";
  }
}

export function buildPageView(input) {
  const params = new URLSearchParams(input.search || "");
  return {
    path: input.path,
    referrer_host: referrerHost(input.referrer) || "",
    local_time: input.localTime,
    tz: input.timeZone || "",
    region: input.region || "",
    device_type: deviceType({
      width: input.screenWidth,
      userAgent: input.userAgent,
      maxTouchPoints: input.maxTouchPoints,
    }),
    browser: browserName(input.userAgent),
    os: osName(input.userAgent),
    screen_w: Number(input.screenWidth) || 0,
    lang: input.language || "",
    utm_source: params.get("utm_source") || "",
    utm_medium: params.get("utm_medium") || "",
    utm_campaign: params.get("utm_campaign") || "",
    session_id: input.sessionId,
  };
}

export function normalizePageView(input, context = {}) {
  const source = input && typeof input === "object" ? input : {};
  const path = pagePath(source.path);
  const session_id = UUID.test(String(source.session_id || "")) ? String(source.session_id).toLowerCase() : null;
  if (!path || !session_id) return { ok: false, error: "invalid" };
  const userAgent = String(context.userAgent || "");
  const requestedDevice = String(source.device_type || "");
  const device_type = DEVICES.has(requestedDevice)
    ? requestedDevice
    : deviceType({ width: source.screen_w, userAgent, maxTouchPoints: 0 });
  const row = {
    path,
    referrer_host: referrerHost(source.referrer_host),
    local_time: wallClock(source.local_time),
    tz: timeZone(source.tz),
    country: resolveCountry(context.countryHeader, source.region || source.country),
    device_type,
    browser: userAgent ? browserName(userAgent) : pick(source.browser, BROWSERS),
    os: userAgent ? osName(userAgent) : pick(source.os, OSES),
    screen_w: screenWidth(source.screen_w),
    lang: language(source.lang),
    utm_source: utm(source.utm_source),
    utm_medium: utm(source.utm_medium),
    utm_campaign: utm(source.utm_campaign),
    session_id,
  };
  return { ok: true, row };
}

export function pacificDay(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Los_Angeles",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

/** Same grouping as public.page_views_daily: day in America/Los_Angeles, path, country. */
export function summarizePageViews(rows) {
  const buckets = new Map();
  for (const row of rows) {
    const day = pacificDay(row.created_at);
    if (!day || !row.path) continue;
    const country = row.country || "";
    const key = `${day}\0${row.path}\0${country}`;
    const current = buckets.get(key) || { day, path: row.path, country, views: 0 };
    current.views += 1;
    buckets.set(key, current);
  }
  return [...buckets.values()].sort(
    (a, b) => a.day.localeCompare(b.day) || a.path.localeCompare(b.path) || a.country.localeCompare(b.country),
  );
}

function wallClock(value) {
  const raw = String(value || "").trim();
  if (!/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}$/.test(raw)) return null;
  return raw.replace("T", " ");
}

function timeZone(value) {
  const raw = String(value || "").trim();
  if (!raw || raw.length > 64) return null;
  if (!/^[A-Za-z0-9_+-]+(?:\/[A-Za-z0-9_+-]+){0,2}$/.test(raw)) return null;
  return raw;
}

function screenWidth(value) {
  const width = Number(value);
  if (!Number.isInteger(width) || width < 0 || width > 10000) return null;
  return width;
}

function language(value) {
  const raw = String(value || "").trim();
  if (!raw || raw.length > 35) return null;
  if (!/^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8}){0,3}$/.test(raw)) return null;
  return raw;
}

function utm(value) {
  const raw = String(value || "").trim();
  if (!raw) return null;
  if (raw.length > 80 || !/^[\w .+~-]+$/.test(raw)) return null;
  return raw;
}

function pick(value, allowed) {
  return allowed.has(value) ? value : "Other";
}

const PAGEVIEW_LIMIT = 60;
const PAGEVIEW_WINDOW_MS = 10 * 60 * 1000;
const MAX_BODY = 4096;

export async function handlePageView(req, deps) {
  const requestOrigin = req.headers.get("origin");
  const origin = requestOrigin && allowedPageViewOrigin(requestOrigin) ? requestOrigin : null;
  if (req.method === "OPTIONS") return pageViewResponse(origin ? 204 : 403, origin);
  if (req.method !== "POST") return pageViewResponse(405, origin);
  if (!origin) return pageViewResponse(403, null);

  const raw = await req.text();
  if (raw.length > MAX_BODY) return pageViewResponse(400, origin);
  let payload;
  try {
    payload = JSON.parse(raw || "{}");
  } catch {
    return pageViewResponse(400, origin);
  }

  const normalized = normalizePageView(payload, {
    countryHeader: req.headers.get("cf-ipcountry") || (req.cf && req.cf.country) || "",
    userAgent: req.headers.get("user-agent") || "",
  });
  if (!normalized.ok) return pageViewResponse(400, origin);

  const db = deps.serviceClient();
  const allowed = await deps.takeRate(db, `pageview:${normalized.row.session_id}`, PAGEVIEW_LIMIT, PAGEVIEW_WINDOW_MS);
  if (!allowed) return pageViewResponse(429, origin);
  const { error } = await db.from("page_views").insert(normalized.row);
  if (error) return pageViewResponse(500, origin);
  return pageViewResponse(204, origin);
}

export function pageViewResponse(status, origin) {
  const headers = {
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type, accept",
    vary: "origin",
  };
  if (origin) headers["access-control-allow-origin"] = origin;
  return new Response(null, { status, headers });
}
