"use client";

import type { ComponentProps } from "react";

/** A native <select> that submits its form on change. Without JS, the form's button does it. */
export function AutoSubmitSelect(props: ComponentProps<"select">) {
  return <select {...props} onChange={(e) => e.currentTarget.form?.requestSubmit()} />;
}
