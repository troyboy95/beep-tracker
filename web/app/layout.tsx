import type { Metadata } from "next";
import { Albert_Sans, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const sans = Albert_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "800"],
  variable: "--font-sans",
  display: "swap",
});

const serif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Beep — Fresher jobs & internships in India",
  description:
    "Openings for 0–2 years of experience, collected daily from company career pages and sorted by role and city.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-IN" className={`${sans.variable} ${serif.variable}`}>
      <body>{children}</body>
    </html>
  );
}
