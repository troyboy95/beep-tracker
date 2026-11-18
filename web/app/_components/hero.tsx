import { getFacets, getLastRefresh } from "@/lib/jobs";
import { formatStamp } from "@/lib/format";
import type { JobFilters } from "@/lib/jobs";
import ui from "./ui.module.css";

/** Static shell part: both reads are cached and expire when the pipeline revalidates. */
export async function Hero({ children }: { children: React.ReactNode }) {
  const [facets, refreshed] = await Promise.all([getFacets(), getLastRefresh()]);

  return (
    <section className={`wrap ${ui.hero}`} aria-labelledby="headline">
      <h1 className={ui.headline} id="headline">
        <span className={ui.headLight}>Fresher jobs &amp; internships</span>
        <span className={ui.headHeavy}>across India.</span>
      </h1>
      <p className={ui.lede}>
        Openings for 0&ndash;2 years of experience, collected daily from the career pages of{" "}
        {facets.companies} companies and sorted by role and city.
      </p>
      {children}
      {refreshed && (
        <p className={ui.stamp}>
          Updated <time dateTime={refreshed}>{formatStamp(refreshed)}</time>
        </p>
      )}
    </section>
  );
}

/** Plain GET form: works without JavaScript; current filters ride along as hidden fields. */
export function SearchForm({ filters }: { filters?: JobFilters }) {
  return (
    <form className={ui.search} action="/" method="get" role="search">
      <label htmlFor="q" className="visually-hidden">
        Search openings
      </label>
      <input
        id="q"
        name="q"
        type="search"
        className={ui.searchInput}
        placeholder="Try “data analyst” or “Razorpay”"
        defaultValue={filters?.q}
        maxLength={100}
        autoComplete="off"
      />
      {filters?.role && <input type="hidden" name="role" value={filters.role} />}
      {filters?.city && <input type="hidden" name="city" value={filters.city} />}
      {filters?.type && <input type="hidden" name="type" value={filters.type} />}
      <button type="submit" className={ui.button}>
        Search
      </button>
    </form>
  );
}
