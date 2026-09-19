# Hosting Rich-HER at rich-her.tech

The hosted copy is the link judges click and the URL on the Devpost submission. **It is not
what you present from** — the venue demo still runs on localhost with Wi-Fi off, for the
reasons in the README's "Before you demo".

## What had to change first

The app held one global session, so every visitor to a public URL would have shared one
portfolio. `server/main.py` now keeps one `Session` per browser, keyed by an `rh_sid`
cookie:

- `session_for(request)` returns that browser's session, creating it on first sight
- a middleware mints the id and sets the cookie
- `SESSIONS` is capped at `MAX_SESSIONS` (200) so a long-running host can't grow forever
- `POST /api/reset` resets only the caller's session

`test_two_browsers_do_not_share_a_portfolio` covers it. Same-origin fetch sends the cookie
automatically, so no frontend change was needed.

## 1. The domain — already done

`rich-her.tech` was registered on 19 Sep 2026 through **Namify** (name.store), with DNS on
orderbox nameservers. It currently has no `A` record, so it resolves nowhere yet — that's
step 3.

DNS is edited in the Namify control panel, not at Render.

## 2. Deploy to Render

`render.yaml` is committed, so Render can read the whole configuration:

1. Push this branch to GitHub.
2. Render dashboard → **New** → **Blueprint** → pick this repo. It reads `render.yaml`.
3. Deploy. First build takes a few minutes; you get a `something.onrender.com` URL.
4. Open it and click through onboarding once to confirm it works.

Without the blueprint, the same thing by hand: a **Web Service**, runtime Python, build
`pip install -r server/requirements.txt`, start
`uvicorn server.main:app --host 0.0.0.0 --port $PORT`.

`python dev.py run` also works as a start command. It reads `$PORT` and binds `0.0.0.0`
when the platform sets one, and falls back to the system Python when there's no `.venv`.

### If the site hangs with no response

Connection opens, TLS completes, then nothing — that means the router has no app to talk
to. In order of likelihood:

1. **The start command binds localhost.** `uvicorn server.main:app --port 8000` listens on
   127.0.0.1, which the router cannot reach. It needs `--host 0.0.0.0 --port $PORT`.
2. **An old `python dev.py run` that required `.venv`.** Render has no `.venv`, so the
   process died on startup. Fixed here — redeploy so the service picks up the new `dev.py`.
3. **Check the branch.** A service built from `main` before this work merged has neither
   `render.yaml` nor per-visitor sessions.

## 3. Point the domain at it

1. Render → your service → **Settings** → **Custom Domains** → add both `rich-her.tech` and
   `www.rich-her.tech`. Render shows the exact records to create.
2. In the **Namify** DNS panel for `rich-her.tech`, add what Render showed you — an `A`
   record at the root (`@`) and a `CNAME` for `www` pointing at your `*.onrender.com`
   hostname. If the panel refuses an `A` record at the root, point `www` with the `CNAME`
   and use Namify's forwarding to send the bare domain to `www`.
3. Wait for propagation — usually minutes. Check with `dig +short rich-her.tech A`; when it
   returns Render's IP you're through. Render then issues the TLS certificate by itself.

## 4. The free-tier catch

Free Render services sleep after a stretch of no traffic, and the next visitor waits
roughly a minute for a cold start. A judge who clicks your link and sees a blank tab for
50 seconds is gone.

Two ways to handle it:

- **Free:** point an uptime pinger (UptimeRobot, cron-job.org) at `https://rich-her.tech/`
  every 10 minutes. Hit `/`, never an `/api/*` path — see the note in `render.yaml`.
- **~$7 for the month:** upgrade the service to a paid instance for the weeks around
  judging, then downgrade. Buys certainty on the one day it matters.

## Known limits of the hosted copy

- Sessions live in memory, so a deploy or a restart clears everyone's replay. The browser's
  own replay log recovers the session on next load.
- `MAX_SESSIONS` is 200; the oldest is dropped past that. Fine for a hackathon, wrong for
  real traffic.
- `QA_LOG` is still process-global and mixes every visitor together. That's intentional —
  it is a tally of how strangers answered the comprehension checks, not per-user data.
