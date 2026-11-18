"use client";

import ui from "./_components/ui.module.css";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="wrap" style={{ paddingBlock: "6rem" }}>
      <h1 className={ui.emptyTitle}>Listings couldn&rsquo;t load.</h1>
      <p className={ui.emptyText} style={{ marginBottom: "1.5rem" }}>
        The job database didn&rsquo;t respond. Try again in a moment.
      </p>
      <button type="button" className={ui.button} onClick={() => reset()}>
        Try again
      </button>
    </main>
  );
}
