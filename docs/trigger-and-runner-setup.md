# Trigger URL and Runner (Webhook) Setup

The manual trigger link (`/api/trigger/run?token=...&target=5`) tells the **web app** to POST to your **agent** at `RUNNER_WEBHOOK_URL`. If you see:

```json
{"ok":false,"error":"Runner unreachable","hint":"..."}
```

it means the web app (e.g. on Vercel) **cannot reach** the agent at that URL.

## Requirements

1. **RUNNER_WEBHOOK_URL must be a public URL**  
   The web app runs in the cloud (Vercel). It cannot reach:
   - `http://localhost:8000`
   - `http://127.0.0.1:8000`
   - Any URL that only works on your own machine or private network  

   Use a URL that is reachable from the internet, e.g.:
   - `https://your-agent.railway.app/run`
   - `https://your-agent.onrender.com/run`
   - `https://your-server.example.com/run`

2. **The agent must be running with the webhook server**  
   Start the agent so it listens for HTTP POSTs:

   ```bash
   cd apps/agent
   python main.py --webhook
   ```

   By default it listens on port 8000 (`WEBHOOK_PORT` to override). It accepts POST at `/run` or `/`.

3. **If you use RUNNER_WEBHOOK_SECRET**  
   Set the same value in:
   - **Web app** (Vercel): `RUNNER_WEBHOOK_SECRET`
   - **Agent** (env): `RUNNER_WEBHOOK_SECRET`  
   The trigger route sends `Authorization: Bearer <RUNNER_WEBHOOK_SECRET>`.

## Local testing

- **Web app locally**: If you run the Next.js app locally and set `RUNNER_WEBHOOK_URL=http://localhost:8000/run`, it will work only from the same machine.
- **Web app on Vercel**: You must deploy the agent to a **public** host and set `RUNNER_WEBHOOK_URL` to that host’s URL (e.g. Railway, Render, Fly.io, or your own server with a public IP/domain).

## Checklist when “Runner unreachable”

- [ ] Agent is running: `python main.py --webhook` (or your deployed process).
- [ ] `RUNNER_WEBHOOK_URL` in the web app (e.g. Vercel) is the **public** URL of the agent, including path `/run` (e.g. `https://xxx.railway.app/run`).
- [ ] From the internet, `curl -X POST <RUNNER_WEBHOOK_URL>` (with `Authorization: Bearer <RUNNER_WEBHOOK_SECRET>` if set) returns 202 or 200.
- [ ] No firewall or hosting policy blocking incoming requests to the agent.
