import Link from "next/link";
import { formatDay } from "@/lib/format";
import { getFacets, getJobs, PAGE_SIZE, type Facets, type Job, type JobFilters } from "@/lib/jobs";
import { hrefFor } from "@/lib/params";
import { AutoSubmitSelect } from "./auto-submit-select";
import ui from "./ui.module.css";

const TYPES: { value: JobFilters["type"]; label: string }[] = [
  { value: "", label: "All" },
  { value: "full_time", label: "Jobs" },
  { value: "internship", label: "Internships" },
];

export async function Listings({ filters }: { filters: JobFilters }) {
  const [facets, result] = await Promise.all([getFacets(), getJobs(filters)]);
  const filtered = Boolean(filters.q || filters.role || filters.city || filters.type);

  return (
    <>
      <FilterBand
        filters={filters}
        facets={facets}
        total={result.kind === "ok" ? result.total : null}
        filtered={filtered}
      />
      <section className="wrap" aria-label="Openings">
        {result.kind === "out_of_range" ? (
          <Empty title="This page is past the end of the results.">
            <Link href={hrefFor(filters, { page: 1 })}>Go to the first page</Link>.
          </Empty>
        ) : result.jobs.length === 0 ? (
          <Empty title="No openings match these filters.">
            Try a broader search, or <Link href="/">clear all filters</Link>.
          </Empty>
        ) : (
          <>
            <JobList jobs={result.jobs} />
            <Pager filters={filters} total={result.total} />
          </>
        )}
      </section>
    </>
  );
}

function FilterBand({
  filters,
  facets,
  total,
  filtered,
}: {
  filters: JobFilters;
  facets: Facets;
  total: number | null;
  filtered: boolean;
}) {
  return (
    <div className={ui.band}>
      <div className={`wrap ${ui.bandInner}`}>
        <form className={ui.filters} action="/" method="get" aria-label="Filter openings">
          {filters.q && <input type="hidden" name="q" value={filters.q} />}
          {filters.type && <input type="hidden" name="type" value={filters.type} />}
          <label className={ui.field}>
            Role
            <AutoSubmitSelect name="role" defaultValue={filters.role} className={ui.select}>
              <option value="">All roles</option>
              {facets.roles.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.value} ({r.count})
                </option>
              ))}
            </AutoSubmitSelect>
          </label>
          <label className={ui.field}>
            City
            <AutoSubmitSelect name="city" defaultValue={filters.city} className={ui.select}>
              <option value="">All cities</option>
              {facets.cities.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.value} ({c.count})
                </option>
              ))}
            </AutoSubmitSelect>
          </label>
          <noscript>
            <button type="submit" className={ui.button}>
              Apply filters
            </button>
          </noscript>
        </form>

        <nav className={ui.segments} aria-label="Opening type">
          {TYPES.map((t) => (
            <Link
              key={t.label}
              href={hrefFor(filters, { type: t.value })}
              className={ui.segment}
              aria-current={filters.type === t.value ? "page" : undefined}
            >
              {t.label}
            </Link>
          ))}
        </nav>

        <p className={ui.count} aria-live="polite">
          {total === null ? null : filtered ? (
            <>
              <strong>{total}</strong> of {facets.total} openings &nbsp;
              <Link href="/" className={ui.clear}>
                Clear filters
              </Link>
            </>
          ) : (
            <>
              <strong>{total}</strong> openings
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function JobList({ jobs }: { jobs: Job[] }) {
  return (
    <>
      <div className={ui.columns} aria-hidden="true">
        <span>Opening</span>
        <span>City</span>
        <span>Role</span>
        <span>Posted</span>
        <span />
      </div>
      <ul className={ui.list}>
        {jobs.map((job) => {
          const date = job.posted_at ?? job.first_seen_at;
          return (
            <li key={job.id} className={ui.row}>
              <div className={ui.main}>
                <a href={job.url} className={ui.title} target="_blank" rel="noopener noreferrer">
                  {job.title}
                </a>
                {job.job_type === "internship" && <span className={ui.tag}>Internship</span>}
                <p className={ui.company}>{job.company}</p>
              </div>
              <div className={ui.meta}>
                <p className={ui.cell}>{job.city}</p>
                <p className={ui.cell}>{job.role}</p>
                <p className={`${ui.cell} ${ui.muted}`}>
                  <time dateTime={date}>{formatDay(date)}</time>
                </p>
              </div>
              <a
                href={job.url}
                className={ui.apply}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`Apply: ${job.title} at ${job.company} (opens employer site)`}
              >
                Apply
              </a>
            </li>
          );
        })}
      </ul>
    </>
  );
}

function Pager({ filters, total }: { filters: JobFilters; total: number }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages === 1) return <div className={ui.pager} />;
  const prev = filters.page > 1 ? hrefFor(filters, { page: filters.page - 1 }) : null;
  const next = filters.page < pages ? hrefFor(filters, { page: filters.page + 1 }) : null;
  return (
    <nav className={ui.pager} aria-label="Pages">
      {prev ? <Link href={prev}>Previous</Link> : <span className={ui.pagerOff}>Previous</span>}
      <span>
        Page {filters.page} of {pages}
      </span>
      {next ? <Link href={next}>Next</Link> : <span className={ui.pagerOff}>Next</span>}
    </nav>
  );
}

function Empty({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={ui.empty}>
      <h2 className={ui.emptyTitle}>{title}</h2>
      <p className={ui.emptyText}>{children}</p>
    </div>
  );
}

export function ListingsSkeleton() {
  return (
    <>
      <div className={ui.band}>
        <div className={`wrap ${ui.bandInner}`} style={{ minHeight: "5.75rem" }} />
      </div>
      <div className="wrap" aria-busy="true" aria-label="Loading openings">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className={ui.skeleton} />
        ))}
      </div>
    </>
  );
}
