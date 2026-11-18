import { Suspense } from "react";
import { Footer, Header } from "./_components/chrome";
import { Hero, SearchForm } from "./_components/hero";
import { Listings, ListingsSkeleton } from "./_components/listings";
import { parseFilters } from "@/lib/params";

type SP = PageProps<"/">["searchParams"];

// searchParams is request-time data: read it only inside <Suspense> so the hero stays in the
// prerendered shell and only the filtered parts stream in.
async function SearchWithParams({ searchParams }: { searchParams: SP }) {
  return <SearchForm filters={parseFilters(await searchParams)} />;
}

async function ListingsWithParams({ searchParams }: { searchParams: SP }) {
  return <Listings filters={parseFilters(await searchParams)} />;
}

export default function Home({ searchParams }: PageProps<"/">) {
  return (
    <>
      <Header />
      <main>
        <Hero>
          <Suspense fallback={<SearchForm />}>
            <SearchWithParams searchParams={searchParams} />
          </Suspense>
        </Hero>
        <Suspense fallback={<ListingsSkeleton />}>
          <ListingsWithParams searchParams={searchParams} />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
