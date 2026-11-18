const TZ = "Asia/Kolkata";

const day = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", timeZone: TZ });
const stamp = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: TZ,
});

/** "12 Nov" — absolute dates keep cached pages correct regardless of when they're served. */
export const formatDay = (iso: string) => day.format(new Date(iso));

/** "18 Nov, 08:02 IST" */
export const formatStamp = (iso: string) => `${stamp.format(new Date(iso))} IST`;
