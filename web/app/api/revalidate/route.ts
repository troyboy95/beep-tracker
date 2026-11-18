import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";
import { JOBS_TAG } from "@/lib/jobs";

/** Called by the pipeline after a run that changed data. `Authorization: Bearer <secret>`. */
export async function POST(request: Request) {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret) {
    return Response.json({ error: "REVALIDATE_SECRET is not configured" }, { status: 500 });
  }

  const given = Buffer.from(request.headers.get("authorization")?.replace(/^Bearer /, "") ?? "");
  const expected = Buffer.from(secret);
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Expire immediately so the next visitor sees the new listings, not a stale copy.
  revalidateTag(JOBS_TAG, { expire: 0 });
  return Response.json({ revalidated: true, at: new Date().toISOString() });
}
