import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { signSvix, signUnsubscribeToken, verifySvix, verifyUnsubscribeToken } from "../supabase/functions/_shared/mailing.js";
import { confirmationEmail, contactAckEmail, contactFrom, maskRecipient, welcomeEmail } from "../supabase/functions/_shared/transactional.js";

const SECRET = "test-unsubscribe-secret";
const TOKEN = "eyJlbWFpbCI6InJlYWRlckBleGFtcGxlLmNvbSIsInNpZCI6InN1Yl8xIn0.hrcb_1Yw__ILl9FHRZ4uXh6YCLAz8IL5TEWyKlMXSmk";

test("unsubscribe token matches the Python vector", async () => {
  const token = await signUnsubscribeToken("sub_1", "Reader@Example.com", SECRET);
  assert.equal(token, TOKEN);
  assert.deepEqual(await verifyUnsubscribeToken(token, SECRET), { sid: "sub_1", email: "reader@example.com" });
  assert.equal(await verifyUnsubscribeToken(token, "other-secret"), null);
});

test("transactional templates stay short and plain", () => {
  const confirm = confirmationEmail({ confirmUrl: "https://openhealthsignals.org/confirm?token=abc" });
  assert.equal(confirm.subject, "Confirm your Open Health Signals email");
  assert.match(confirm.text, /^Confirm this address for Open Health Signals\./);
  assert.match(confirm.text, /https:\/\/openhealthsignals.org\/confirm\?token=abc/);
  assert.equal(confirm.replyTo, "contact@openhealthsignals.org");
  assert.equal(confirm.text.toLowerCase().includes("causes"), false);

  const welcome = welcomeEmail({
    unsubscribeUrl: "https://openhealthsignals.org/unsubscribe?token=abc",
    listUnsubscribeUrl: "https://fn.example/unsubscribe?token=abc",
    postalAddress: "",
  });
  assert.equal(welcome.subject, "Welcome to Open Health Signals");
  assert.match(welcome.text, /^Welcome to Open Health Signals\./);
  assert.match(welcome.text, /Inflammation Signal Monitor/);
  assert.equal(welcome.text.toLowerCase().split("not medical advice").length - 1, 1);
  assert.match(welcome.text, /about once a week/i);
  assert.match(welcome.text, /FAERS/);
  assert.equal(welcome.text.includes("San Jose"), false);
  assert.equal(welcome.html.includes("#5c564c"), false);
  assert.equal(welcome.headers["List-Unsubscribe"], "<https://fn.example/unsubscribe?token=abc>");
  assert.equal(welcome.headers["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click");

  const withPostal = welcomeEmail({
    unsubscribeUrl: "https://openhealthsignals.org/unsubscribe?token=abc",
    listUnsubscribeUrl: "https://fn.example/unsubscribe?token=abc",
    postalAddress: "PO Box 1, San Jose, CA",
  });
  assert.match(withPostal.text, /PO Box 1, San Jose, CA/);
  assert.match(withPostal.html, /PO Box 1, San Jose, CA/);

  const ack = contactAckEmail({ interestLabel: "Media", excerpt: "The first lines" });
  assert.equal(ack.text.startsWith("Thanks, we got your message and will reply within a few days."), true);
  assert.match(ack.text, /The first lines/);
  assert.equal(contactFrom("Open Health Signals <briefing@openhealthsignals.org>"), "Open Health Signals <contact@openhealthsignals.org>");
  assert.equal(contactFrom("Ops <onboarding@resend.dev>"), "Ops <onboarding@resend.dev>");
  assert.equal(maskRecipient("jane@example.com"), "j***@example.com");
  assert.equal(maskRecipient("J@domain.test"), "J***@domain.test");
  assert.equal(maskRecipient("not-an-email"), "***");
});

test("Svix fixture matches the Python signature", async () => {
  const fixture = JSON.parse(readFileSync(new URL("./fixtures/resend_bounce.json", import.meta.url), "utf8"));
  const body = new TextEncoder().encode(fixture.body);
  const signed = await signSvix({
    secret: fixture.secret,
    svixId: fixture.svix_id,
    timestamp: fixture.svix_timestamp,
    body,
  });
  assert.equal(signed, fixture.svix_signature);
  assert.equal(
    await verifySvix({
      secret: fixture.secret,
      body,
      svixId: fixture.svix_id,
      svixTimestamp: fixture.svix_timestamp,
      svixSignature: fixture.svix_signature,
      now: Number(fixture.svix_timestamp) * 1000,
    }),
    true,
  );
  assert.equal(
    await verifySvix({
      secret: fixture.secret,
      body,
      svixId: fixture.svix_id,
      svixTimestamp: fixture.svix_timestamp,
      svixSignature: "v1,forged",
      now: Number(fixture.svix_timestamp) * 1000,
    }),
    false,
  );
});
