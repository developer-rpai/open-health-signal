// Token and Svix helpers shared by the edge functions.
// The byte format matches inflammon/mailing.py. tests/mailing.test.mjs locks the vector.

export function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

export function validEmail(email) {
  const normalized = normalizeEmail(email);
  if (normalized.includes(" ") || normalized.split("@").length !== 2) return false;
  const [local, domain] = normalized.split("@");
  return Boolean(local) && domain.includes(".") && !domain.startsWith(".") && !domain.endsWith(".");
}

function bytesToB64Url(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

function b64UrlToBytes(value) {
  const padded = value + "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded.replaceAll("-", "+").replaceAll("_", "/"));
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
  return out;
}

function b64ToBytes(value) {
  const padded = value + "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
  return out;
}

async function hmacSha256(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    typeof secret === "string" ? new TextEncoder().encode(secret) : secret,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const data = typeof message === "string" ? new TextEncoder().encode(message) : message;
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, data));
}

export async function sha256Hex(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function newConfirmToken() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return bytesToB64Url(bytes);
}

export async function signUnsubscribeToken(subscriberId, email, secret) {
  const payload = JSON.stringify({ email: normalizeEmail(email), sid: String(subscriberId) });
  const body = bytesToB64Url(new TextEncoder().encode(payload));
  const signature = await hmacSha256(secret, body);
  return `${body}.${bytesToB64Url(signature)}`;
}

export async function verifyUnsubscribeToken(token, secret) {
  if (!token || !secret || !token.includes(".")) return null;
  const [body, signature] = token.split(".");
  const expected = bytesToB64Url(await hmacSha256(secret, body));
  if (expected.length !== signature.length) return null;
  let mismatch = 0;
  for (let i = 0; i < expected.length; i += 1) mismatch |= expected.charCodeAt(i) ^ signature.charCodeAt(i);
  if (mismatch !== 0) return null;
  try {
    const payload = JSON.parse(new TextDecoder().decode(b64UrlToBytes(body)));
    const sid = String(payload.sid || "");
    const email = normalizeEmail(payload.email || "");
    if (!sid || !email) return null;
    return { sid, email };
  } catch {
    return null;
  }
}

export function svixSecretBytes(secret) {
  const part = secret.startsWith("whsec_") ? secret.slice(6) : secret;
  return b64ToBytes(part);
}

export async function signSvix({ secret, svixId, timestamp, body }) {
  const prefix = new TextEncoder().encode(`${svixId}.${timestamp}.`);
  const signed = new Uint8Array(prefix.length + body.length);
  signed.set(prefix, 0);
  signed.set(body, prefix.length);
  const digest = await hmacSha256(svixSecretBytes(secret), signed);
  let binary = "";
  for (const byte of digest) binary += String.fromCharCode(byte);
  return `v1,${btoa(binary)}`;
}

export async function verifySvix({ secret, body, svixId, svixTimestamp, svixSignature, now = Date.now(), tolerance = 300 }) {
  if (!secret || !svixId || !svixTimestamp || !svixSignature) return false;
  const stamp = Number(svixTimestamp);
  if (!Number.isFinite(stamp)) return false;
  if (Math.abs(now / 1000 - stamp) > tolerance) return false;
  const expected = await signSvix({ secret, svixId, timestamp: svixTimestamp, body });
  return svixSignature.split(" ").some((presented) => presented.length === expected.length && timingSafeEqual(presented, expected));
}

function timingSafeEqual(left, right) {
  let mismatch = 0;
  for (let i = 0; i < left.length; i += 1) mismatch |= left.charCodeAt(i) ^ right.charCodeAt(i);
  return mismatch === 0;
}

export function suppressionFromResendEvent(event) {
  const status = { "email.bounced": "bounced", "email.complained": "complained" }[event?.type];
  if (!status) return null;
  const recipients = event?.data?.to;
  const list = Array.isArray(recipients) ? recipients : recipients ? [recipients] : [];
  const email = normalizeEmail(list[0] || "");
  if (!email) return null;
  return { email, status };
}

export function oneClickBody(raw) {
  return String(raw || "").includes("List-Unsubscribe=One-Click");
}

export const INTEREST_TYPES = [
  "research_collaboration",
  "data_expansion",
  "code_contribution",
  "custom_analysis",
  "media",
  "sponsorship",
];
