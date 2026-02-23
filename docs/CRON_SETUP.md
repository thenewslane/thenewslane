# Cron setup — pulling content on a schedule

The pipeline (collect → predict → brand safety → classify → content → video → media → publish) runs in **apps/agent** (Python). To have content pulled automatically (default: once per day), you need something that **runs the pipeline on a schedule**.

---

## Option 1: Built-in scheduler (recommended for a 24/7 server)

Run the agent with the built-in loop so it runs every N minutes without any external cron:

```bash
cd apps/agent
source .venv/bin/activate   # or your env
export PIPELINE_INTERVAL_MINUTES=5
python main.py --schedule
```

- Runs the first batch immediately, then every `PIPELINE_INTERVAL_MINUTES` (default: 1440 = once per day).
- Leave this process running (e.g. on Railway, Render, a VPS, or a systemd service).
- No Vercel Cron or Inngest required.

---

## Option 2: Vercel Cron + webhook to your runner

If you want Vercel to trigger the pipeline on a schedule:

1. **Deploy the agent somewhere that can receive HTTP** (e.g. Railway, Render, Fly.io). Expose a small HTTP endpoint that runs one pipeline batch (e.g. `POST /run` that calls `run_pipeline()` and returns 200).

2. **Set environment variables in Vercel:**
   - `CRON_SECRET` — a random secret (e.g. `openssl rand -hex 24`). Vercel Cron will send this as `Authorization: Bearer <CRON_SECRET>`.
   - `RUNNER_WEBHOOK_URL` — the URL of your agent’s trigger endpoint (e.g. `https://your-agent.railway.app/run`).

3. **Add a cron schedule in Vercel** (Dashboard → Project → Settings → Cron Jobs, or `vercel.json`):

   In **apps/web/vercel.json** you can add:

   ```json
   {
     "crons": [
       {
         "path": "/api/cron/run-pipeline",
         "schedule": "0 3 * * *"
       }
     ]
   }
   ```

   Then in Vercel Dashboard → Settings → Environment Variables, add `CRON_SECRET` and (optional) `RUNNER_WEBHOOK_URL`. Vercel will call `GET /api/cron/run-pipeline` on the configured schedule (default: once daily at 03:00 UTC) with `Authorization: Bearer <CRON_SECRET>`.

4. **Implement the agent’s `/run` endpoint** (e.g. in **apps/agent**) so that when it receives a POST from your web app, it runs one pipeline batch. Example (Flask): a route that calls `run_pipeline()` and returns 200. Your `RUNNER_WEBHOOK_URL` should point to this route.

If `RUNNER_WEBHOOK_URL` is not set, the API route still returns 200 so the cron does not fail; you must run the pipeline by other means (e.g. Option 1).

---

## Option 3: Inngest

To use Inngest for scheduling:

1. Run the Inngest dev server and connect your app (see [Inngest](https://www.inngest.com)).
2. Start the agent with Inngest: `python main.py --inngest`. This starts a Flask server that Inngest calls on the configured CRON (default: once daily).
3. Ensure the agent is reachable at a public URL and that Inngest is configured to call it.

---

## Summary

| Method              | Where it runs        | What to do |
|---------------------|----------------------|------------|
| `main.py --schedule`| Your server (24/7)   | Run once, leave running; interval via `PIPELINE_INTERVAL_MINUTES`. |
| Vercel Cron + webhook | Vercel + your runner | Set `CRON_SECRET` and `RUNNER_WEBHOOK_URL`; add cron in Vercel; implement `/run` in agent. |
| Inngest             | Inngest + your agent | Run `main.py --inngest` and connect Inngest to your agent URL. |

If “the cron is not running to pull content”, confirm that one of the above is actually in place (e.g. a long-running `main.py --schedule` or a cron hitting `/api/cron/run-pipeline` with `RUNNER_WEBHOOK_URL` set to a live runner).
