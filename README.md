# ModIO-Collection-Downloader

**ModIO-Collection-Downloader** is a simple command-line tool to download entire mod collections from [mod.io](https://mod.io) — no config files, no arguments needed. Just run it and follow the prompts.

---

## Features

- **Interactive setup** — the script asks you everything it needs step by step
- **Live game search** — type a game name and get instant suggestions from mod.io
- **Private collection support** — works with OAuth tokens for non-public collections
- **Live download progress** — spinner, progress bar, and file size update in-place
- **Auto-extracts ZIPs** — downloaded archives are unpacked automatically
- **Retry on failure** — each mod retries up to 5 times before giving up
- **Clean summary** — see exactly what succeeded, was skipped, or failed
- **No dependencies** — uses only Python's standard library

---

## Requirements

- **Python 3.7 or higher**
- A **mod.io API key** (free) — get one at [mod.io/me/access](https://mod.io/me/access)
- An **OAuth token** (optional) — only needed for private collections

---

## Setup

### Windows

1. **Install Python**
   Download and install Python from [python.org](https://www.python.org/downloads/).
   During installation, make sure to check **"Add Python to PATH"**.

2. **Download the script**
   Either clone this repo or just download `ModIO-Collection-Downloader.py` directly.

3. **Open a terminal**
   Press `Win + R`, type `cmd`, press Enter.

4. **Run the script**
   ```
   python ModIO-Collection-Downloader.py
   ```

---

### macOS

1. **Check if Python is installed**
   Open the Terminal app and run:
   ```
   python3 --version
   ```
   If you see a version number you're good. If not, install Python from [python.org](https://www.python.org/downloads/) or via [Homebrew](https://brew.sh):
   ```
   brew install python
   ```

2. **Download the script**
   Either clone this repo or download `ModIO-Collection-Downloader.py` directly.

3. **Run the script**
   ```
   python3 ModIO-Collection-Downloader.py
   ```

---

### Linux

1. **Check if Python is installed**
   ```
   python3 --version
   ```
   If it's not installed, use your package manager:
   ```bash
   # Debian / Ubuntu
   sudo apt install python3

   # Fedora
   sudo dnf install python3

   # Arch
   sudo pacman -S python
   ```

2. **Download the script**
   Either clone this repo or download `ModIO-Collection-Downloader.py` directly.

3. **Run the script**
   ```
   python3 ModIO-Collection-Downloader.py
   ```

   Optionally, make it executable so you can run it directly:
   ```bash
   chmod +x ModIO-Collection-Downloader.py
   ./ModIO-Collection-Downloader.py
   ```

---

## Usage

Just run the script — it will guide you through everything:

```
╔══════════════════════════════════════╗
║   mod.io Collection Downloader       ║
╚══════════════════════════════════════╝

  Welcome! Answer a few quick questions and we'll get started.

  Step 1/4 – API Key
  ? Your mod.io API Key: ••••••••••••••••

  Step 2/4 – OAuth Token (optional)
  ? Use an OAuth token for private collections? [y/N]: n

  Step 3/4 – Select a game
  ? Game name or ID: anno

  Games found:
  1) Anno 1800  [ID: 4321]  – Build the city of your dreams
  2) Anno 117   [ID: 8765]  – Rome is just the beginning
  0) Search again

  ? Your choice (number): 1

  Step 4/4 – Collection ID
  ? Collection ID (number): 12345
  ? Download folder [default: ./mods_download]:

  ─── Summary ────────────────────────────────
  Game ID    : 4321
  Collection : 12345
  Token      : No
  Save path  : /home/user/mods_download
  ───────────────────────────────────────────

  ? Everything correct? Start downloading? [Y/n]:
```

Downloads then run with a live progress line per mod:

```
  ✓ [12/12] Better Taxes Overhaul        ████████████████████ 100.0%  6.2 MB/6.2 MB
```

And finish with a summary:

```
  ═══ Download complete! ═══

  ✓ Succeeded :  11
  ⚠ Skipped   :   1
  ✗ Failed    :   0

  Saved to: /home/user/mods_download
```

---

## Getting Your API Key

1. Go to [mod.io/me/access](https://mod.io/me/access)
2. Log in or create a free account
3. Scroll to **API Access** and copy your API key

## Getting an OAuth Token (private collections only)

1. Go to [mod.io/me/access](https://mod.io/me/access)
2. Scroll to **OAuth 2 Access**
3. Generate a token and copy it

---

## Finding a Collection ID

The collection ID is the number at the right side of collection's page on mod.io.

For example:

![alt text](https://github.com/TamashiiMon/ModIO-Collection-Downloader/blob/main/assets/Screenshot_20260402_015806.png?raw=true)

---

## License

MIT — do whatever you want with it.
