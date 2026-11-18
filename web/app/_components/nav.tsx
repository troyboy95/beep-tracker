"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useTransition,
  type ComponentProps,
} from "react";
import ui from "./ui.module.css";

/**
 * Client-side navigation for filters, search and paging.
 *
 * Every change is a router navigation inside a transition with `scroll: false`, so:
 *  - the current results stay on screen (dimmed) until the new ones arrive (no skeleton flash,
 *    no layout shift, no document reload),
 *  - the scroll position is kept; <Results> only moves it after the new results render.
 */
type Nav = {
  pending: boolean;
  navigate: (href: string, opts?: { replace?: boolean }) => void;
};

const NavContext = createContext<Nav | null>(null);

export function NavProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const navigate = useCallback<Nav["navigate"]>(
    (href, opts) =>
      startTransition(() => {
        if (opts?.replace) router.replace(href, { scroll: false });
        else router.push(href, { scroll: false });
      }),
    [router],
  );
  return <NavContext value={{ pending, navigate }}>{children}</NavContext>;
}

export function useNav(): Nav {
  const nav = useContext(NavContext);
  if (!nav) throw new Error("useNav must be used inside <NavProvider>");
  return nav;
}

/** A real link (prefetch, open-in-new-tab, no-JS) that navigates in a transition on plain click. */
export function NavLink({ href, ...props }: ComponentProps<typeof Link> & { href: string }) {
  const { navigate } = useNav();
  return (
    <Link
      href={href}
      scroll={false}
      {...props}
      onClick={(e) => {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
          return;
        e.preventDefault();
        navigate(href);
      }}
    />
  );
}

/**
 * Wraps the result list. Dims while a navigation is pending; once new results have rendered
 * (navKey changed), brings the list top into view only if the user is scrolled past it.
 */
export function Results({ navKey, children }: { navKey: string; children: React.ReactNode }) {
  const { pending } = useNav();
  const ref = useRef<HTMLDivElement>(null);
  const lastKey = useRef(navKey);

  useEffect(() => {
    if (lastKey.current === navKey) return; // first mount: leave scroll alone
    lastKey.current = navKey;
    const el = ref.current;
    if (!el || el.getBoundingClientRect().top >= 0) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
  }, [navKey]);

  return (
    <div ref={ref} className={ui.results} aria-busy={pending}>
      {children}
    </div>
  );
}
