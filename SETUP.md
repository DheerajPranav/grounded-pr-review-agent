# Production setup — going live

Everything runs locally with **zero** external accounts (baseline mode, in-memory spine, in-process
queue). This checklist wires the real services. Each is optional and independent — the app degrades
gracefully when a credential is missing.

## 0. Local, no accounts
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,server]"
python -m grounded serve            # ingress on :8000, dashboard at http://localhost:8000
```

## 1. Groq — the LLM reviewer (free)
1. Sign up at https://console.groq.com → **API Keys** → create a key.
2. Put it in `.env`: `GROQ_API_KEY=gsk_...`, and set `REVIEW_MODE=specialists` (or `llm`).
3. Optional guard rail: `DAILY_CAP_USD=1.00`.

## 2. GitHub App — receive PRs and post reviews
1. GitHub → **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. **Webhook URL**: `https://<your-deploy-host>/webhook/github` (see step 4). **Webhook secret**:
   generate a random string → put it in `.env` as `GITHUB_WEBHOOK_SECRET`.
3. **Permissions**: Pull requests → Read & write; Contents → Read-only. **Subscribe to events**:
   Pull request.
4. Install the App on your repo(s). Create an installation token (or a fine-grained PAT for testing)
   → `.env` as `GITHUB_TOKEN`.

## 3. Tiger Cloud — the durable data spine (optional)
1. Create a free service at https://console.cloud.tigerdata.com (new accounts get credit).
2. Copy the Postgres connection string → `.env` as `TIGER_DATABASE_URL=postgres://...?sslmode=require`.
3. Apply the schema: `pip install -e ".[data]" && python -m grounded migrate`.
   (Without this, the app keeps memory in-process and skips durable persistence — no error.)

## 4. Deploy (Railway)
The repo ships a `Dockerfile`, `Procfile`, and `railway.json`.
1. Push to GitHub (already done).
2. Railway → **New Project → Deploy from GitHub repo** → pick `grounded-pr-review-agent`.
3. Add the env vars from `.env` in the Railway dashboard. Add Railway's **Redis** and (optionally)
   point `TIGER_DATABASE_URL` at Tiger Cloud.
4. The `release` phase runs `python -m grounded migrate`; the `web` process serves the webhook; add
   a `worker` service running `arq grounded.job_queue.arq_worker.WorkerSettings` for the async queue.
5. Put the deploy URL's `/webhook/github` back into the GitHub App webhook (step 2).

## Full stack locally (Docker)
```bash
docker compose up --build          # Tiger (TimescaleDB+pgvector) + Redis + app + worker
docker compose run --rm app python -m grounded migrate
```

## Verify it's live
- `GET /healthz` → `{"status":"ok", ...}`
- Open a PR on an installed repo → a review appears on the PR; the run shows on the dashboard `/`.
