# Babynames3
# שם טוב — Name Explorer

Israeli Jewish girls' name swiper · 3,603 names from CBS 1949–2024

Data source: [Israel CBS — Personal Names publication 391, December 2025](https://www.cbs.gov.il/he/mediarelease/DocLib/2025/391/11_25_391b.pdf) · [Download Excel data](https://www.cbs.gov.il/he/mediarelease/DocLib/2025/391/11_25_391t1.xlsx)

---

## Setup (Windows dev server)

```bat
git clone https://github.com/YOUR_USERNAME/shem-tov.git
cd shem-tov
setup.bat
run.bat
```

App starts on **http://localhost:5000** and prints your local + Tailscale IPs.

---

## iOS workflow (Working Copy → GitHub Actions → auto-deploy)

Since your server is Windows and only reachable via Tailscale,
GitHub can't webhook directly to it. Instead, GitHub Actions connects
*into* your Tailscale network and SSHes to deploy.

```
You (iOS)                GitHub                  Dev server (Windows)
   │                        │                           │
   │── push ──────────────► │                           │
   │                        │── Actions starts          │
   │                        │── joins Tailscale ───────►│
   │                        │── SSH: git pull + restart ►│
   │                        │                           │ ✓ deployed
```

### One-time setup

#### 1. Enable OpenSSH on Windows
Settings → System → Optional Features → Add "OpenSSH Server"

```powershell
# Then start it
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

#### 2. Create a Tailscale OAuth client
Go to [Tailscale Admin → Settings → OAuth clients](https://login.tailscale.com/admin/settings/oauth)
- Create a client with **Devices: write** scope
- Tag it: `tag:github-actions`
- Save the **Client ID** and **Secret**

In your Tailscale ACL, allow the tag to connect:
```json
"tagOwners": { "tag:github-actions": [] }
```

#### 3. Add GitHub repository secrets
Go to your repo → **Settings → Secrets → Actions**, add:

| Secret | Value |
|--------|-------|
| `TS_OAUTH_CLIENT_ID` | Tailscale OAuth client ID |
| `TS_OAUTH_SECRET` | Tailscale OAuth secret |
| `DEV_HOST` | Your machine's Tailscale IP or name (e.g. `100.x.x.x`) |
| `DEV_USER` | Your Windows username |
| `DEV_PASSWORD` | Your Windows password (or use SSH key — see below) |

#### 4. Update the deploy path in the workflow
Edit `.github/workflows/deploy.yml` — change this line to your actual path:
```yaml
cd C:\path\to\shem_tov
```

#### Done
Push from Working Copy → Actions deploys automatically in ~30 seconds.

---

### Using an SSH key instead of password (recommended)

```powershell
# On Windows server — generate a key
ssh-keygen -t ed25519 -f $HOME\.ssh\github_deploy

# Add public key to authorized_keys
Add-Content "$HOME\.ssh\authorized_keys" (Get-Content "$HOME\.ssh\github_deploy.pub")
```

Then in GitHub secrets: add `DEV_SSH_KEY` with the *private* key contents,
and in `.github/workflows/deploy.yml` replace `password:` with `key:`:
```yaml
key: ${{ secrets.DEV_SSH_KEY }}
```

---

## Running

```bat
run.bat                                           :: HTTP (no PWA offline)
run.bat --cert HOST.crt --key HOST.key            :: HTTPS (enables PWA offline)
run.bat --host 0.0.0.0 --debug                    :: with auto-reload
deploy.bat                                        :: pull + restart
```

---

## PWA offline support (requires HTTPS)

Service workers — which cache the app for offline use — **only work over HTTPS** (browsers block them on plain HTTP). To enable full offline support:

### Option A: Tailscale certificate (recommended)

Tailscale provides free, real TLS certificates for any machine on your tailnet.

```powershell
# 1. Generate cert for your Tailscale hostname (e.g. mypc.tail-abc.ts.net)
tailscale cert mypc.tail-abc.ts.net

# 2. Run the app with HTTPS
run.bat --cert mypc.tail-abc.ts.net.crt --key mypc.tail-abc.ts.net.key

# 3. Access the app at:
#    https://mypc.tail-abc.ts.net:5003
```

After the first successful HTTPS load, the service worker caches the entire app — subsequent loads work even when the server is off.

### Option B: Local network only (HTTP)

The app still works on HTTP — it uses `localStorage` fallbacks for all data. But the page itself can't load when the server is down since there's no service worker cache.

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/names` | Full dataset (cached) |
| GET | `/api/state` | Liked + skipped lists |
| POST | `/api/state` | Save progress |
| DELETE | `/api/state` | Clear all progress |
| GET | `/api/settings` | User preferences |
| POST | `/api/settings` | Save preferences |
| GET | `/api/ratings` | Star ratings |
| POST | `/api/ratings` | Save star ratings |
| GET | `/api/version` | Git version (hash + date) |

---

## Project layout

```
shem_tov/
├── .github/workflows/deploy.yml  ← auto-deploy via Tailscale SSH
├── app.py
├── requirements.txt
├── setup.bat / run.bat / deploy.bat
├── static/
│   ├── names.json
│   ├── manifest.json
│   ├── sw.js
│   └── icons/
└── templates/
    └── index.html
```
