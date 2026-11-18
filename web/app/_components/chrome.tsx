import Link from "next/link";
import ui from "./ui.module.css";

const REPO = "https://github.com/troyboy95/beep-tracker";

/** A single heartbeat blip: the "beep". Draws itself once on load. */
export function Mark() {
  return (
    <svg className={ui.mark} viewBox="0 0 34 22" aria-hidden="true">
      <path
        className={ui.markPath}
        d="M1 12h8l3-8 5 15 4-11 2 4h10"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="square"
        strokeLinejoin="miter"
      />
    </svg>
  );
}

export function Header() {
  return (
    <header className={`wrap ${ui.header}`}>
      <Link href="/" className={ui.brand}>
        <Mark />
        beep
      </Link>
      <nav className={ui.nav} aria-label="Site">
        <a href="#how">How it works</a>
        <a href={REPO}>Source code</a>
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className={ui.footer} id="how">
      <div className={`wrap ${ui.footerGrid}`}>
        <div>
          <Link href="/" className={ui.brand}>
            <Mark />
            beep
          </Link>
          <p className={ui.footerLine}>Apply on the employer&rsquo;s own site.</p>
        </div>
        <div>
          <h2 className={ui.footerHeading}>How it works</h2>
          <p className={ui.footerText}>
            Every morning, Beep reads the public job boards that companies publish on Greenhouse,
            Lever, Ashby and SmartRecruiters. It keeps openings located in India that ask for at
            most two years of experience, merges duplicates, and uses a language model to sort each
            one by role and city.
          </p>
          <p className={ui.footerText}>
            Tags are automatic and can be wrong. Always check the full posting before you apply.{" "}
            <a href={REPO}>Read the source code</a>.
          </p>
        </div>
      </div>
    </footer>
  );
}
