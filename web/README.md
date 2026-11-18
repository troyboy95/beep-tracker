# Beep: web

Next.js 16 (App Router, Cache Components) frontend for Beep. It reads from Supabase with the read-only publishable key; see the [root README](../README.md) for the whole system.

```bash
cp ../.env.example .env.local   # keep only the "Web" section: SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, REVALIDATE_SECRET
npm install
npm run dev                     # http://localhost:3000
```

| Script | What |
|---|---|
| `npm run build` | Production build (needs the env vars: the static shell is prerendered from the DB) |
| `npm run lint` / `npm run typecheck` | ESLint / TypeScript |
| `npm run gen:types` | Regenerate `lib/database.types.ts` from the DB schema (bash; needs `DATABASE_URL` and `npx supabase`) |

## How data flows

- `lib/jobs.ts`: every query is a `'use cache'` function tagged `jobs` with `cacheLife('hours')`.
- `app/api/revalidate`: `POST` with `Authorization: Bearer $REVALIDATE_SECRET` expires the `jobs` tag. The pipeline calls it after each run that changed data.
- `app/page.tsx`: the hero is part of the prerendered shell. Search params are read inside `<Suspense>`, so only the filtered list streams in.
- Search is Postgres full-text (`websearch` syntax) over title, company, role, city and description.
