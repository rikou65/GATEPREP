# Self-Hosting GATE Study OS for free (or near-free)

This guide gets your personal GATE Study OS running on a **free-tier stack** with **persistent data** that survives restarts — solving the ephemeral-DB problem you hit on the development environment.

**Total cost**: $0/month for typical personal use (within free-tier limits).
**Total time**: ~30 minutes if you already have Google accounts ready.

## The stack we'll use

| Layer | Provider | Free tier limit | Notes |
|---|---|---|---|
| MongoDB | **MongoDB Atlas (M0)** | 512 MB storage, shared CPU | More than enough for personal use |
| Backend (FastAPI) | **Render** (web service) | 750 hrs/mo, sleeps after 15 min idle | Or use Railway ($5 trial credit/mo) |
| Frontend (React) | **Vercel** | Unlimited static hosting | Auto-deploys on `git push` |
| Auth (Google OAuth) | Google Cloud Console | Free | You already have this set up |

> **Why not all-Vercel?** Vercel serverless has a 10s function timeout on free tier — too short for some Drive/YouTube imports.

---

## Step 0 — Push your code to GitHub

Already done from your project ✅. If not: in the chat input, click **"Save to Github"**.

Make sure the repo contains the new config files we just generated:
- `render.yaml` (root) — Render Infrastructure-as-Code
- `vercel.json` (root) — Vercel build config
- `frontend/.env.production.example` — frontend env template
- `backend/.env.example` — backend env template

---

## Step 1 — Create the MongoDB Atlas cluster (5 min)

1. Sign up at https://www.mongodb.com/cloud/atlas/register (use the same Google account you're already using).
2. Create a new project: **"gate-study-os"**.
3. **Build a Database** → choose **M0 (Free)** → AWS, pick the region closest to you.
4. Cluster name: **`gate-os`**.
5. **Database Access** (left sidebar):
   - Add new database user. Username **`gateuser`**, password **(generate & copy this — you only see it once)**.
   - Privileges: **Atlas admin** (simplest; tighten later if you want).
6. **Network Access** → **Add IP Address** → **"Allow access from anywhere" (`0.0.0.0/0`)**.
   *Yes this is fine for a free personal project — DB is protected by the password.*
7. Back on **Database** → click **Connect** on your cluster → **Drivers** → Python → copy the connection string. It looks like:
   ```
   mongodb+srv://gateuser:<password>@gate-os.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   Replace `<password>` with the one you generated. **Save this string — it's your `MONGO_URL`.**
8. Pick a DB name: **`gate_study_os`** (this becomes your `DB_NAME`).

---

## Step 2 — Deploy the backend on Render (10 min)

1. Sign up at https://render.com using GitHub.
2. **New +** → **Blueprint** → connect your repo → Render auto-detects `render.yaml`.
3. Click **Apply**. Render creates the `gate-os-backend` web service for you.
4. Once it shows up, click into the service → **Environment** → set these secrets (the blueprint marks them as "sync: false" so Render asks you to fill them in):

   | Key | Value |
   |---|---|
   | `MONGO_URL` | the Atlas connection string from Step 1.7 |
   | `DB_NAME` | `gate_study_os` |
   | `JWT_SECRET` | run `openssl rand -hex 32` locally, paste output |
   | `GOOGLE_DRIVE_CLIENT_ID` | from your Google Cloud Console OAuth client |
   | `GOOGLE_DRIVE_CLIENT_SECRET` | same |
   | `GOOGLE_DRIVE_REDIRECT_URI` | `https://<your-render-host>/api/drive/callback`  ← fill in after deploy gives you the URL |
   | `FRONTEND_URL` | `https://<your-vercel-host>`  ← fill in after Step 3 |
   | `AUTH_PROVIDER_URL` | `PLACEHOLDER_AUTH_PROVIDER_URL` |
   | `MISTRAL_API_KEY` | Your Mistral AI API key — required for PDF OCR ingestion. Get one at https://console.mistral.ai/ |

5. Hit **Save**, Render redeploys. Wait for green **Live** badge. Your URL is now `https://gate-os-backend-xxxx.onrender.com`.
6. **Update Google Cloud Console**:
   - Open your existing OAuth 2.0 Client → **Authorized redirect URIs** → add:
     ```
     https://gate-os-backend-xxxx.onrender.com/api/drive/callback
     ```
   - (Keep the previous development URL too if you still use that.)
7. **Update `GOOGLE_DRIVE_REDIRECT_URI` on Render** to that same URL, save & redeploy.

> **First-request cold start**: Render's free tier sleeps after 15 min of no traffic. First request after sleep takes ~30s to wake. Subsequent requests are fast. To avoid: upgrade to Render Starter ($7/mo) or hit `/api/health` every 10 min from a free cron service (e.g. cron-job.org).

---

## Step 3 — Deploy the frontend on Vercel (5 min)

1. Sign up at https://vercel.com using GitHub.
2. **Add New… → Project** → import the same repo.
3. Vercel detects `vercel.json` and asks for env vars. Set:

   | Key | Value |
   |---|---|
   | `REACT_APP_BACKEND_URL` | `https://gate-os-backend-xxxx.onrender.com` (from Step 2.5) |

   > **After Vite migration** (see `IMPLEMENTATION_PLAN.md` Phase 6): the env key changes to `VITE_BACKEND_URL` and the build output directory changes from `build/` to `dist/`. Update Vercel's Output Directory setting accordingly at that time.

4. **Deploy**. ~2 minutes later you have `https://gate-study-os-yourname.vercel.app`.
5. **Go back to Render** → update the `FRONTEND_URL` env var to this Vercel URL → redeploy.
6. **Google Cloud Console** → Authorized redirect URIs on the Google OAuth login client (if separate) → add the Vercel host.

---

## Step 4 — First-run sanity check (2 min)

1. Open your Vercel URL → click **Sign in with Google** → complete OAuth.
2. Go to **Settings → Google Drive → Connect**. OAuth back to your live backend → ✅ Connected.
3. Click **Resources → Sync from Drive**. If you previously uploaded PDFs into `GATEPREP/…` on Drive, they'll re-attach to your new persistent DB. **You won't lose them again.**
4. Add a question. Reload. It's still there. **You're done.**

---

## Step 5 — One-time migration from preview container (optional)

If you want to bring across data you created on the preview before today, here's the manual route (we don't have a CLI yet because the preview container is opaque):

1. On the preview, in any window where you have it open: open DevTools → Network → trigger e.g. **GET /api/questions** → save the JSON response.
2. Repeat for `/api/pyqs`, `/api/playlists`, `/api/resources` (metadata only — actual PDFs already live in your Drive).
3. For each list, POST the items back to your new Render backend. There's a tiny helper script at `scripts/migrate_export.py` you can run locally:
   ```bash
   python scripts/migrate_export.py --from-preview https://preview-url \
                                    --to https://gate-os-backend-xxxx.onrender.com \
                                    --token <your-jwt-from-localStorage>
   ```

If you don't have anything important on the preview, **skip this step entirely** — the Drive sync in Step 4.3 gets your PDFs back, and questions/PYQs you can just re-add.

---

## Troubleshooting

**Render build fails with `motor` or `pymongo` issues.**
→ Check the build logs. Your `requirements.txt` is pinned; the blueprint sets Python 3.11 which matches our dev environment.

**Login works but every API call returns 401.**
→ `FRONTEND_URL` on the backend is wrong → backend rejects CORS. Fix and redeploy.

**Google Drive OAuth says `redirect_uri_mismatch`.**
→ The exact URL you put in Google Cloud Console must match `GOOGLE_DRIVE_REDIRECT_URI`. *No trailing slash, no `/oauth/` segment* — it should look like `https://…/api/drive/callback`.

**Cold-start delays drive me crazy.**
→ Two options: (1) upgrade Render to Starter ($7/mo, always-on), or (2) hit `https://yourbackend/api/health` from cron-job.org every 10 minutes.

**Atlas free tier full.**
→ At 512 MB you're storing ~hundreds of thousands of questions + every attempt log. If you ever get near, upgrade to M2 ($9/mo) or run a cleanup of old `question_attempts`.

---

## Why this stack vs. alternatives

- **Why Render and not Fly.io?** Fly is great but has a small free tier and credit-card requirement. Render's free web service is generous *and* the blueprint format is dead-simple.
- **Why MongoDB Atlas and not a self-hosted Mongo on the same VM?** Free tier on Atlas, automatic backups, no ops. Self-hosting Mongo on a free-tier VM means you're babysitting it.
- **Why not Cloudflare Pages for the frontend?** Vercel's React build pipeline is more battle-tested for CRA projects like ours. Once the Vite migration (Phase 6) is done, Cloudflare Pages becomes a viable and faster alternative.

---

## When to upgrade

| If… | Upgrade |
|---|---|
| Cold starts annoy you | Render Starter ($7/mo) — always-on backend |
| You want a custom domain | Vercel custom domain (free) + Render custom domain (free on paid plans) |
| DB > 400 MB | Atlas M2 ($9/mo) — dedicated CPU + 2 GB |
| You add a second user | All of the above tiers still cover it; nothing changes architecturally |

Have fun. Your data is now yours forever.
