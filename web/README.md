# Dashboard

Static Next.js app for Inflammation Signal Monitor. The repository README at the root covers the pipeline, methods, and deploy steps.

```bash
npm install
npm run dev -- --hostname 127.0.0.1 --port 43123
npm run build   # writes web/out
```

Pages read the JSON snapshot in `data/`, produced by `make refresh` from the repository root. Newsletter pages read `data/newsletter/`, produced by `make newsletter`. Set the Vercel project root to this directory.

The subscribe form needs `NEXT_PUBLIC_BUTTONDOWN_USERNAME` in `.env.local` before `npm run dev` or `npm run build`. The Buttondown API key does not go in this directory. See the repository README.
