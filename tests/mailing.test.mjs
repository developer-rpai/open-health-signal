import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { signSvix, signUnsubscribeToken, verifySvix, verifyUnsubscribeToken } from "../supabase/functions/_shared/mailing.js";

const SECRET = "test-unsubscribe-secret";
const TOKEN = "eyJlbWFpbCI6InJlYWRlckBleGFtcGxlLmNvbSIsInNpZCI6InN1Yl8xIn0.hrcb_1Yw__ILl9FHRZ4uXh6YCLAz8IL5TEWyKlMXSmk";

test("unsubscribe token matches the Python vector", async () => {
  const token = await signUnsubscribeToken("sub_1", "Reader@Example.com", SECRET);
  assert.equal(token, TOKEN);
  assert.deepEqual(await verifyUnsubscribeToken(token, SECRET), { sid: "sub_1", email: "reader@example.com" });
  assert.equal(await verifyUnsubscribeToken(token, "other-secret"), null);
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
