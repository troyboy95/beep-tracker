import type { JobFilters, JobType } from "./jobs";

type RawParams = Record<string, string | string[] | undefined>;

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

/** Parse and bound URL search params. Unknown values simply match nothing. */
export function parseFilters(sp: RawParams): JobFilters {
  const type = one(sp.type);
  const page = Number.parseInt(one(sp.page), 10);
  return {
    q: one(sp.q).trim().slice(0, 100),
    role: one(sp.role).slice(0, 80),
    city: one(sp.city).slice(0, 80),
    type: (type === "internship" || type === "full_time" ? type : "") as JobType,
    page: Number.isFinite(page) && page > 0 ? Math.min(page, 1000) : 1,
  };
}

/** Build a listing URL from filters; any filter change resets to page 1 unless given. */
export function hrefFor(f: JobFilters, overrides: Partial<JobFilters> = {}): string {
  const next = { ...f, page: 1, ...overrides };
  const qs = new URLSearchParams();
  if (next.q) qs.set("q", next.q);
  if (next.role) qs.set("role", next.role);
  if (next.city) qs.set("city", next.city);
  if (next.type) qs.set("type", next.type);
  if (next.page > 1) qs.set("page", String(next.page));
  const s = qs.toString();
  return s ? `/?${s}` : "/";
}
