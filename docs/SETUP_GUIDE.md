# Setup Guide — Run This POC Locally

This is a complete, start-to-finish guide for getting this repo running on
your own machine. It assumes no prior Python experience. Follow it top to
bottom; each step tells you exactly what to type and what you should see.

Covers: getting the code, installing Python, installing dependencies (and
*where* they actually go), running the test suite and demo, running the MCP
server, and getting it a public HTTPS URL for Oracle AI Agent Studio to
call — either by deploying to Render.com (recommended, especially on
locked-down corporate laptops) or by tunneling your local machine.

**One rule that matters on every step below:** on Windows (PowerShell,
cmd.exe, or Git Bash), Python is invoked as `python`. On macOS/Linux, it's
`python3`. Windows virtual environments never create a `python3.exe` — only
`python.exe` — so typing `python3` on Windows silently runs a *different,
unrelated* Python installation from your PATH instead of this project's
virtual environment, which produces a confusing `ModuleNotFoundError` even
though everything was installed correctly. Every command below is written
for macOS/Linux (`python3`); if you're on Windows, mentally swap in
`python` for every `python3` you see, in every step, including inside the
virtual environment.

---

## 0. What you'll end up with

- A folder on your machine with this project's code.
- A Python **virtual environment** — a self-contained folder (`.venv/`)
  *inside the project* that holds the one dependency this project needs
  (the `mcp` package). Nothing gets installed system-wide; nothing here can
  conflict with other Python projects on your machine.
- The ability to run the validation demo and the MCP server locally.

---

## 1. Install prerequisites

You need **Python 3.9 or newer** and **git** (or you can download the code
as a ZIP instead of using git — see step 2).

**Check if you already have Python:**
```bash
python3 --version        # Windows: python --version
```
If that prints `Python 3.9.x` or higher, you're set — skip to step 2.

**If you don't have it:**

| OS | How to install |
|---|---|
| macOS | Install [Homebrew](https://brew.sh) if you don't have it, then: `brew install python3` |
| Windows | Download the installer from [python.org/downloads](https://www.python.org/downloads/). During install, **check the box "Add python.exe to PATH"** — this is the #1 cause of "command not found" errors later. |
| Linux (Debian/Ubuntu) | `sudo apt update && sudo apt install python3 python3-venv python3-pip` |

**Check if you have git:**
```bash
git --version
```
If missing: macOS (`brew install git`), Windows ([git-scm.com/downloads](https://git-scm.com/downloads)), Linux (`sudo apt install git`).

---

## 2. Get the code

**Option A — with git (recommended):**
```bash
git clone https://github.com/bensonbaby-svg/Oracle-Recruiting.git
cd Oracle-Recruiting
git checkout claude/fortive-data-validation-agent-gctvor
```

**Option B — no git:** go to
[github.com/bensonbaby-svg/Oracle-Recruiting](https://github.com/bensonbaby-svg/Oracle-Recruiting),
switch the branch dropdown to `claude/fortive-data-validation-agent-gctvor`
(this work isn't merged to `main` yet), then click **Code → Download ZIP**,
unzip it anywhere, and open a terminal and `cd` into the unzipped folder.

From here on, every command assumes your terminal's current directory is
that project folder (the one containing `main.py` and `requirements.txt`).

---

## 3. Create and activate the virtual environment

A **virtual environment** is just a folder that holds its own private copy
of Python packages, separate from your system Python. We create one named
`.venv` inside the project folder. Once activated, any `pip install` you
run puts packages inside `.venv/` — not system-wide.

Pick the row for your shell:

| Shell | Create | Activate |
|---|---|---|
| macOS / Linux (bash/zsh) | `python3 -m venv .venv` | `source .venv/bin/activate` |
| Windows — Git Bash (MINGW64) | `python -m venv .venv` | `source .venv/Scripts/activate` |
| Windows — PowerShell | `python -m venv .venv` | `.venv\Scripts\Activate.ps1` |
| Windows — cmd.exe | `python -m venv .venv` | `.venv\Scripts\activate.bat` |

Notes:
- Windows always uses a `Scripts/` folder for these files; macOS/Linux uses
  `bin/`. If you get `No such file or directory` on `.venv/bin/activate`
  while on Windows, you used the wrong row above — switch to `Scripts/`.
- If PowerShell blocks activation with an execution-policy error, run
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once, then
  retry the `Activate.ps1` line.

**How to know it worked:** your terminal prompt should now show `(.venv)`
at the start of the line, e.g. `(.venv) you@machine Oracle-Recruiting %`.
Every command below assumes it's still showing `(.venv)` — if you close
and reopen your terminal, you must re-run the **activate** command again
(not the create/`venv` command — that folder already exists, you just need
to re-enter it for this terminal session).

---

## 4. Install dependencies

With `(.venv)` active:
```bash
pip install -r requirements.txt
```
`pip` (unlike `python3`/`python`) reliably resolves inside the active venv
on every OS, so this line is identical everywhere. It reads
`requirements.txt` (currently just `mcp`, the Model Context Protocol SDK)
and installs it — and everything it depends on — into `.venv/`. Takes
under a minute.

**Verify it worked:**
```bash
python3 -c "from importlib.metadata import version; print('mcp installed OK, version', version('mcp'))"
```
(Windows: `python` instead of `python3` — see the rule at the top of this guide.)

---

## 5. Run the test suite

```bash
python3 -m unittest discover -s tests -v
```
Expect `OK` at the bottom with 8 tests passed. This confirms the validation
rule catalog itself works correctly before you touch anything else.

---

## 6. Run the demo

```bash
python3 main.py
```
This validates the 17 mock Canada employee records in
`data/sample_hcm_extract_canada.csv` and prints each flagged exception
(Critical/Warning, which rule, which field, why). It also writes one HTML
email digest per HR/data owner into the `output/` folder — open one of
those `.html` files in a browser to see what the actual notification email
would look like.

---

## 7. Run the MCP server

```bash
python3 mcp_server/server.py
```
This starts a server listening on port 8000, serving the MCP protocol at
`http://localhost:8000/mcp`. Leave this terminal running — it's now ready
to accept tool calls (from a local test client, or eventually from Oracle
AI Agent Studio).

To confirm it's alive, from a **second terminal** (no venv/activation
needed for `curl`):
```bash
curl -i -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```
You should get back `HTTP/1.1 200 OK` and a JSON body containing
`"serverInfo":{"name":"fortive-hcm-adp-validator", ...}`.

Stop the server any time with `Ctrl+C` in its terminal. Running it locally
like this is enough to prove the logic works (steps 5-7) — you only need
step 8 once you're ready to actually register it as a tool in Oracle AI
Agent Studio.

---

## 8. Get it a public HTTPS URL (needed to register in Oracle AI Agent Studio)

Studio runs in Oracle's cloud and can't reach `localhost` on your laptop —
it needs a public HTTPS URL. Two paths; **Path A is recommended** and is
the only one that reliably works on a locked-down corporate laptop, since
nothing runs or installs locally at all.

### Path A — Deploy to Render.com (recommended)

Everything happens in Render's cloud via your browser and GitHub login —
no local `.exe`, no tunnel, nothing for corporate endpoint security to
block.

1. Go to [render.com](https://render.com) and sign up/log in (GitHub login
   is easiest).
2. Click **New +** → **Web Service**.
3. **Connect a repository** → authorize Render against
   `bensonbaby-svg/Oracle-Recruiting`
   (`https://github.com/bensonbaby-svg/Oracle-Recruiting.git`). If it
   offers a "public Git repo" URL field instead of an account connection,
   paste that URL directly.
4. Set **Branch** to `claude/fortive-data-validation-agent-gctvor` — this
   work isn't merged to `main` yet, so the default branch won't have it.
5. **Environment/Runtime**: Python 3.
6. **Build Command**: `pip install -r requirements.txt`
7. **Start Command**: `python mcp_server/server.py`
8. **Instance Type**: the free tier is fine for a demo.
9. Click **Create Web Service**. Render builds and deploys automatically —
   watch the build log for `Uvicorn running on http://0.0.0.0:<port>` to
   confirm it started. You'll get a URL like
   `https://oracle-recruiting.onrender.com`.
10. Your MCP endpoint for Studio is that URL plus `/mcp`:
    ```
    https://oracle-recruiting.onrender.com/mcp
    ```

**Verify it** from any terminal (no venv or local server needed — this is
hitting Render's cloud, not your machine):
```bash
curl -i -X POST https://oracle-recruiting.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```
Expect `HTTP/1.1 200 OK` with `"serverInfo":{"name":"fortive-hcm-adp-validator"...}`.

**Free-tier note:** Render spins the service down after a period of
inactivity; the first request after idle time can take 30-60 seconds while
it wakes back up. That's expected, not a bug — subsequent requests are fast.

### Path B — Local tunnel (only if your machine allows it)

If you're not on a restricted corporate laptop, you can instead expose the
server you started in step 7 directly from your machine. Try, in order:

- **Cloudflare quick tunnel** (needs to install/run `cloudflared`):
  ```bash
  cloudflared tunnel --url http://localhost:8000
  ```
- **SSH tunnel** (no install — uses the `ssh` client you already have):
  ```bash
  ssh -R 80:localhost:8000 nokey@localhost.run
  ```

Either prints a public URL — append `/mcp` to it for Studio. Keep the
server (step 7) and the tunnel both running the whole time Studio needs to
reach it; if either restarts, the URL changes and you'll need to
re-register it.

**If you hit any of these, stop and switch to Path A instead** — they're
all signs of corporate endpoint security blocking local execution, not
something to keep working around:
- `This operation is disabled by Group Policy: Enable Windows Package Manager`
- Unable to execute a downloaded `.exe`
- `Connection to localhost.run closed.` immediately after connecting

Local tunnels (either path) are for demo/testing only regardless of
whether they work — the URL is temporary and disappears when you close the
terminal. For anything beyond a one-off demo (real Fortive data, a
persistent agent), Render's free tier is still just a demo tier too — move
to real infrastructure (OCI Compute, Container, or Function) at that point
instead; ask if you want steps for that path.

---

## 9. Register the tool in Oracle AI Agent Studio

See `docs/oracle_agent_studio_setup.md`, section **2a**, for the exact
click-by-click steps (Tools → New Tool → Tool Type: MCP → paste the URL
from step 8, Path A or B → select tools → test).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `.venv/bin/activate: No such file or directory` | You're on Windows and used the macOS/Linux row from the step 3 table. Use `source .venv/Scripts/activate` (Git Bash) or the PowerShell/cmd equivalents instead. |
| `.venv\Scripts\Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use `activate.bat` in cmd.exe instead of PowerShell. |
| Prompt doesn't show `(.venv)` | The virtual environment isn't activated — re-run the activate command from step 3 (no need to recreate the folder). |
| `pip install` fails with permission errors | You likely forgot to activate the virtual environment first — re-check for `(.venv)` in your prompt. |
| `ModuleNotFoundError: No module named 'mcp'` when running the server | If your prompt doesn't show `(.venv)`, activate it (step 3) first. If it **does** show `(.venv)` and you're on Windows, you almost certainly typed `python3` instead of `python` — Windows venvs have no `python3.exe`, so `python3` silently runs an unrelated Python from your PATH instead of the venv. Confirm with `which python` (Git Bash) that it resolves inside `.venv/Scripts/`, then re-run using `python`, not `python3`. `pip show mcp` will correctly show the package installed in `.venv` throughout this — that's not a sign the install is broken, since `pip` (unlike `python3`) does resolve inside the venv correctly. |
| Port 8000 already in use (local run) | Run `python3 mcp_server/server.py --port 8001` instead, and adjust the tunnel/curl commands to match. |
| `cloudflared` not found after install | Open a new terminal window so your PATH refreshes. |
| `This operation is disabled by Group Policy: Enable Windows Package Manager` | winget is blocked by corporate policy — skip installing cloudflared via winget and use Path A (Render) instead. |
| Downloaded `cloudflared.exe` won't run / "blocked by your organization" | Corporate endpoint security is blocking new executables — switch to Path A (Render), which needs no local `.exe`. |
| `Connection to localhost.run closed.` right after running the SSH tunnel command | Corporate network is likely blocking/killing SSH port-forwarding specifically (common even when plain SSH is allowed). Switch to Path A (Render). |
| Render build fails | Check the build log for the actual error — most often a typo in the Build/Start Command (should be exactly `pip install -r requirements.txt` and `python mcp_server/server.py`) or the wrong branch selected in step 4. |
| First request to the Render URL is very slow or times out | Expected on the free tier after a period of inactivity — it takes 30-60 seconds to spin back up. Retry the same `curl` command once more. |
| `curl: (35) schannel: next InitializeSecurityContext failed: CRYPT_E_NO_REVOCATION_CHECK` when curling the Render URL | This is Windows' native TLS library failing to check certificate revocation status — common behind a corporate SSL-inspecting proxy/firewall. It's unrelated to whether the Render deployment itself is working. Add `--ssl-no-revoke` to the curl command: `curl -i --ssl-no-revoke -X POST https://.../mcp ...`. |
