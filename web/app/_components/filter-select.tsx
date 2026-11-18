"use client";

import type { ComponentProps } from "react";
import type { JobFilters } from "@/lib/jobs";
import { hrefFor } from "@/lib/params";
import { useNav } from "./nav";

type Props = Omit<ComponentProps<"select">, "name" | "onChange" | "defaultValue"> & {
  name: "role" | "city";
  filters: JobFilters;
};

/** Role/city select: navigates in a transition on change. Without JS, the form's button submits. */
export function FilterSelect({ name, filters, ...props }: Props) {
  const { navigate } = useNav();
  return (
    <select
      // Remount when the URL value changes elsewhere (e.g. "Clear filters").
      key={filters[name]}
      name={name}
      defaultValue={filters[name]}
      onChange={(e) => navigate(hrefFor(filters, { [name]: e.target.value }))}
      {...props}
    />
  );
}
