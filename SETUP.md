# Setup — accounts & secrets I need from you to take it live

Nothing here is created yet. The code scaffold runs offline; going live needs
these. None of these secrets ever get committed — they live in Vercel env vars
and a local `.env` (gitignored). Give me the values in chat and I'll mask them
in the same step, or set them straight in Vercel yourself.

## 1. Slack app (free)
- Create a Slack app at api.slack.com/apps → "From scratch" → pick a workspace
  (a throwaway/personal workspace is fine for the demo).
- I need, once created:
  - **Bot User OAuth Token** (`xoxb-...`)
  - **Signing Secret**
  - App-level token (`xapp-...`) only if we use Socket Mode (we won't for Vercel).
- Scopes I'll ask you to add: `app_mentions:read`, `chat:write`, `commands`,
  `im:history`, `im:read`, `im:write`.
- This is the one piece only you can create (it's tied to your Slack login).

## 2. Vercel project (you already have Vercel)
- A new project linked to this repo. I can create and link it once the GitHub
  repo exists under your account.

## 3. Database — Neon Postgres (free tier)
- A Neon project + database with the `pgvector` extension enabled.
- I need the **connection string** (`postgres://...`).

## 4. Model provider (pick one to start; adapter makes it swappable)
- **OpenRouter** API key (`sk-or-...`) — lets you compare many models, good for
  the eval story — or an **Anthropic** API key if you'd rather start there.

## 5. GitHub
- A repo under your GitHub account (`RafaelC00`) to push this to — public, since
  it's portfolio. I'll run a pre-public audit before anything goes public.

---

### What I can do without any of the above
Scaffold and write all the code, the knowledge-base seed, the tool logic, the
eval suite, and the README — everything runs/tests locally with mocked Slack +
a local model via Ollama. The real tokens are only needed for the live demo URL.

### Order I'd suggest
1. GitHub repo (so Vercel can link) → 2. Neon DB → 3. model key →
4. Slack app last (quickest once everything else answers it).
