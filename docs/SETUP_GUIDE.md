# Setup Guide — Run This POC Locally

This is a complete, start-to-finish guide for getting this repo running on
your own machine. It assumes no prior Python experience. Follow it top to
bottom; each step tells you exactly what to type and what you should see.

Covers: getting the code, installing Python, installing dependencies (and
*where* they actually go), running the test suite and demo, running the MCP
server, and exposing it for Oracle AI Agent Studio to call.

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
python3 --version
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

## 3. Create the virtual environment (where dependencies actually go)

A **virtual environment** is just a folder that holds its own private copy
of Python packages, separate from your system Python. We create one named
`.venv` inside the project folder. Once activated, any `pip install` you
run puts packages inside `.venv/lib/...` — not system-wide.

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
If PowerShell blocks this with an execution-policy error, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
then retry the `Activate.ps1` line.

**Windows (Command Prompt / cmd.exe):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (Git Bash / MINGW64):** the venv module still creates a
Windows-style `Scripts/` folder here, not `bin/` — use:
```bash
python3 -m venv .venv
source .venv/Scripts/activate
```
If you see `bash: .venv/bin/activate: No such file or directory`, that
means you tried the macOS/Linux path (`bin/`) instead of `Scripts/` — this
is the fix.

**How to know it worked:** your terminal prompt should now show `(.venv)`
at the start of the line, e.g. `(.venv) you@machine Oracle-Recruiting %`.
Every command below assumes it's still showing `(.venv)` — if you close
and reopen your terminal, you must re-run the `activate` step (not the
`venv` creation step, just activation) before continuing.

---

## 4. Install dependencies

With `(.venv)` active:
```bash
pip install -r requirements.txt
```
This reads `requirements.txt` (currently just `mcp`, the Model Context
Protocol SDK) and installs it — and everything it depends on — into
`.venv/`. You'll see a list of packages downloading; it takes under a
minute.

**Verify it worked:**
```bash
python3 -c "from importlib.metadata import version; print('mcp installed OK, version', version('mcp'))"
```
(Use `python` instead of `python3` on Windows if `python3` isn't recognized.)

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

To confirm it's alive, from a **second terminal**:
```bash
curl -i -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```
You should get back `HTTP/1.1 200 OK` and a JSON body containing
`"serverInfo":{"name":"fortive-hcm-adp-validator", ...}`.

Stop the server any time with `Ctrl+C` in its terminal.

---

## 8. Expose it publicly (only needed to register in Oracle AI Agent Studio)

Studio runs in Oracle's cloud and can't reach `localhost` on your laptop —
it needs a public HTTPS URL. For a quick demo (no real employee data
involved, since we're only using the mock CSV), use a temporary tunnel:

**Install cloudflared** (no account needed for a quick tunnel):
| OS | Command |
|---|---|
| macOS | `brew install cloudflared` |
| Windows | `winget install --id Cloudflare.cloudflared` |
| Linux | See Cloudflare's install instructions for your distro (`cloudflared` package) |

**Start the tunnel** (in a third terminal, while the server from step 7 is
still running):
```bash
cloudflared tunnel --url http://localhost:8000
```
It prints a URL like `https://random-words.trycloudflare.com`. Your MCP
endpoint to give Oracle AI Agent Studio is:
```
https://random-words.trycloudflare.com/mcp
```

Keep both the server (step 7) and the tunnel running for as long as you
need Studio to be able to reach it. If you restart either one, the tunnel
URL changes — re-register the new URL in Studio.

This tunnel approach is for demo/testing only. For anything beyond that
(real Fortive data, a persistent agent), host the server on real
infrastructure (OCI Compute, Container, or Function) instead — ask if you
want steps for that path.

---

## 9. Register the tool in Oracle AI Agent Studio

See `docs/oracle_agent_studio_setup.md`, section **2a**, for the exact
click-by-click steps (Tools → New Tool → Tool Type: MCP → paste the URL
from step 8 → select tools → test).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` (Windows) | Use `python` instead, or reinstall Python with "Add to PATH" checked. |
| `.venv\Scripts\Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use `activate.bat` in cmd.exe instead of PowerShell. |
| Prompt doesn't show `(.venv)` | The virtual environment isn't activated — re-run the `activate` command from step 3 (you don't need to recreate it with `python -m venv .venv` again). |
| `pip install` fails with permission errors | You likely forgot to activate the virtual environment first — re-check for `(.venv)` in your prompt. |
| Port 8000 already in use | Run `python3 mcp_server/server.py --port 8001` instead, and adjust the tunnel/curl commands to match. |
| `cloudflared` not found after install | Open a new terminal window so your PATH refreshes. |
