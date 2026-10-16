# Dashboard

Static Next.js app for Inflammation Signal Monitor. The repository README at the root covers the pipeline, methods, and deploy steps.

```bash
npm install
npm run dev -- --hostname 127.0.0.1 --port 43123
npm run build   # writes web/out
```

Pages read the JSON snapshot in `data/`, produced by `make refresh` from the repository root. Newsletter pages read `data/newsletter/`, produced by `make newsletter`. Set the Vercel project root to this directory.

Subscribe, confirm, contact, and approve call `NEXT_PUBLIC_FUNCTIONS_BASE`. For a local dry run, point that at `http://127.0.0.1:43124` and run `python -m inflammon.local_functions` from the repository root. Do not put the Supabase service role or the Resend key in this directory.
