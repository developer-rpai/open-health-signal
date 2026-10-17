export async function takeRate(db, bucket, limit, windowMs) {
  const now = Date.now();
  const { data } = await db.from("rate_limits").select("hits,window_start").eq("bucket", bucket).maybeSingle();
  if (!data || now - new Date(data.window_start).getTime() >= windowMs) {
    await db.from("rate_limits").upsert({ bucket, hits: 1, window_start: new Date(now).toISOString() });
    return true;
  }
  if (data.hits >= limit) return false;
  await db.from("rate_limits").update({ hits: data.hits + 1 }).eq("bucket", bucket);
  return true;
}
