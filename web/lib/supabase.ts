import { createClient } from "@supabase/supabase-js";
import type { Database } from "./database.types";

const url = process.env.SUPABASE_URL;
const key = process.env.SUPABASE_PUBLISHABLE_KEY;

if (!url || !key) {
  throw new Error("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be set (see .env.example)");
}

// Publishable key: read-only through RLS (active jobs, the dedup view, non-sensitive run columns).
// Used only from server code; nothing here is sent to the browser.
export const supabase = createClient<Database>(url, key, {
  auth: { persistSession: false, autoRefreshToken: false },
});
