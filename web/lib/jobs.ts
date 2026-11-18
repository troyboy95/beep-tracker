import { cacheLife, cacheTag } from "next/cache";
import { supabase } from "./supabase";

/** Every query here is cached and tagged; the pipeline expires the tag after each run. */
export const JOBS_TAG = "jobs";
export const PAGE_SIZE = 25;

export type JobType = "" | "internship" | "full_time";

export type JobFilters = {
  q: string;
  role: string;
  city: string;
  type: JobType;
  page: number;
};

export type Job = {
  id: number;
  title: string;
  company: string;
  role: string | null;
  city: string | null;
  job_type: string | null;
  url: string;
  posted_at: string | null;
  first_seen_at: string;
};

export type JobsPage =
  | { kind: "ok"; jobs: Job[]; total: number }
  | { kind: "out_of_range" };

export async function getJobs(f: JobFilters): Promise<JobsPage> {
  "use cache";
  cacheTag(JOBS_TAG);
  cacheLife("hours");

  let query = supabase
    .from("public_jobs")
    .select("id,title,company,role,city,job_type,url,posted_at,first_seen_at", {
      count: "exact",
    });
  if (f.q) query = query.textSearch("search_tsv", f.q, { type: "websearch", config: "english" });
  if (f.role) query = query.eq("role", f.role);
  if (f.city) query = query.eq("city", f.city);
  if (f.type === "internship") query = query.eq("job_type", "internship");
  if (f.type === "full_time") query = query.neq("job_type", "internship");

  const from = (f.page - 1) * PAGE_SIZE;
  const { data, count, error } = await query
    .order("posted_at", { ascending: false, nullsFirst: false })
    .order("first_seen_at", { ascending: false })
    .order("id")
    .range(from, from + PAGE_SIZE - 1);

  // PostgREST answers 416 / PGRST103 when the requested page is past the last row.
  if (error?.code === "PGRST103") return { kind: "out_of_range" };
  if (error) throw new Error(`Listings query failed: ${error.message}`);
  return { kind: "ok", jobs: (data ?? []) as Job[], total: count ?? 0 };
}

export type Facet = { value: string; count: number };
export type Facets = { roles: Facet[]; cities: Facet[]; companies: number; total: number };

// Catch-all buckets go last in the city list, after real cities.
const CITY_BUCKETS = ["Remote (India)", "Multiple cities", "Other (India)"];

export async function getFacets(): Promise<Facets> {
  "use cache";
  cacheTag(JOBS_TAG);
  cacheLife("hours");

  // A few hundred rows: counting in JS is cheaper than another view. Revisit past ~10k rows.
  const { data, error } = await supabase.from("public_jobs").select("role,city,company");
  if (error) throw new Error(`Facets query failed: ${error.message}`);

  const tally = (values: (string | null)[]) => {
    const m = new Map<string, number>();
    for (const v of values) if (v) m.set(v, (m.get(v) ?? 0) + 1);
    return [...m].map(([value, count]) => ({ value, count }));
  };
  const rows = data ?? [];
  const roles = tally(rows.map((r) => r.role)).sort((a, b) => b.count - a.count);
  const cities = tally(rows.map((r) => r.city)).sort((a, b) => {
    const ab = CITY_BUCKETS.indexOf(a.value);
    const bb = CITY_BUCKETS.indexOf(b.value);
    if (ab !== bb) return ab - bb; // -1 (real city) sorts before buckets
    return b.count - a.count;
  });
  return {
    roles,
    cities,
    companies: new Set(rows.map((r) => r.company)).size,
    total: rows.length,
  };
}

export async function getLastRefresh(): Promise<string | null> {
  "use cache";
  cacheTag(JOBS_TAG);
  cacheLife("hours");

  const { data, error } = await supabase
    .from("ingest_runs")
    .select("finished_at")
    .in("status", ["success", "partial"])
    .not("finished_at", "is", null)
    .order("finished_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw new Error(`Refresh status query failed: ${error.message}`);
  return data?.finished_at ?? null;
}
