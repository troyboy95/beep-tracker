"use client";

import { useEffect, useState } from "react";
import type { JobFilters } from "@/lib/jobs";
import { hrefFor } from "@/lib/params";
import { useNav } from "./nav";
import ui from "./ui.module.css";

export const MIN_QUERY = 4;
const DEBOUNCE_MS = 400;
const NO_FILTERS: JobFilters = { q: "", role: "", city: "", type: "", page: 1 };

const ready = (q: string) => q.length === 0 || q.length >= MIN_QUERY;

/**
 * Search fires as you type: debounced, and only once the query has MIN_QUERY characters
 * (or is cleared). The button and Enter run the same rule. Without JS, the form is a GET.
 */
export function SearchForm({ filters = NO_FILTERS }: { filters?: JobFilters }) {
  const { navigate } = useNav();
  const [value, setValue] = useState(filters.q);
  // The query this box last sent. A different `filters.q` means the URL changed elsewhere
  // (Clear filters, back button), so the box follows it, without clobbering live typing.
  const [sent, setSent] = useState(filters.q);
  const [seenQ, setSeenQ] = useState(filters.q);
  if (filters.q !== seenQ) {
    setSeenQ(filters.q);
    if (filters.q !== sent) {
      setSent(filters.q);
      setValue(filters.q);
    }
  }

  const q = value.trim();

  useEffect(() => {
    if (!ready(q) || q === sent) return;
    const t = setTimeout(() => {
      setSent(q);
      navigate(hrefFor(filters, { q }), { replace: true }); // typing shouldn't flood history
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [q, sent, filters, navigate]);

  const short = q.length > 0 && q.length < MIN_QUERY;

  return (
    <form
      className={ui.searchBlock}
      action="/"
      method="get"
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        if (!ready(q) || q === sent) return;
        setSent(q);
        navigate(hrefFor(filters, { q }));
      }}
    >
      <div className={ui.search}>
        <label htmlFor="q" className="visually-hidden">
          Search openings
        </label>
        <input
          id="q"
          name="q"
          type="search"
          className={ui.searchInput}
          placeholder="Try “data analyst” or “Razorpay”"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          maxLength={100}
          autoComplete="off"
          aria-describedby="q-hint"
        />
        {filters.role && <input type="hidden" name="role" value={filters.role} />}
        {filters.city && <input type="hidden" name="city" value={filters.city} />}
        {filters.type && <input type="hidden" name="type" value={filters.type} />}
        <button type="submit" className={ui.button}>
          Search
        </button>
      </div>
      {/* Space is always reserved, so the hint never shifts the layout. */}
      <p id="q-hint" className={ui.hint} aria-live="polite">
        {short ? `Type at least ${MIN_QUERY} characters to search.` : " "}
      </p>
    </form>
  );
}
