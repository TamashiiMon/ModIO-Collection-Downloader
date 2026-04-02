#!/usr/bin/env python3
"""
mod.io Collection Downloader – Interactive CLI
"""

import json
import time
import zipfile
import itertools
import sys
import os
import re
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}

SPINNER = itertools.cycle(["|", "/", "-", "\\"])

# ─────────────────────────────────────────────
#  ANSI helpers
# ─────────────────────────────────────────────

def clr(text, code):
    return f"\033[{code}m{text}\033[0m"

def bold(t):   return clr(t, "1")
def dim(t):    return clr(t, "2")
def green(t):  return clr(t, "32")
def yellow(t): return clr(t, "33")
def cyan(t):   return clr(t, "36")
def red(t):    return clr(t, "31")

def clear_line():
    print("\r\033[K", end="", flush=True)

def print_header():
    os.system("cls" if os.name == "nt" else "clear")
    print(bold(cyan("╔══════════════════════════════════════╗")))
    print(bold(cyan("║") + "   mod.io Collection Downloader       " + bold(cyan("║"))))
    print(bold(cyan("╚══════════════════════════════════════╝")))
    print()

def ask(prompt, password=False):
    """Simple input prompt with consistent styling."""
    try:
        if password:
            import getpass
            value = getpass.getpass(f"  {cyan('?')} {bold(prompt)}: ")
        else:
            value = input(f"  {cyan('?')} {bold(prompt)}: ").strip()
        return value
    except (KeyboardInterrupt, EOFError):
        print(f"\n\n{yellow('Cancelled.')}")
        sys.exit(0)

def ask_yes_no(prompt, default=False):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"  {cyan('?')} {bold(prompt)} {dim(hint)}: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{yellow('Cancelled.')}")
            sys.exit(0)
        if answer in ("", None):
            return default
        if answer in ("j", "ja", "y", "yes"):
            return True
        if answer in ("n", "nein", "no"):
            return False
        print(f"  {yellow('Please enter y or n.')}")

# ─────────────────────────────────────────────
#  API helpers
# ─────────────────────────────────────────────

def base_url(game_id: int) -> str:
    return f"https://g-{game_id}.modapi.io/v1"


def make_request(url: str, token: str = None) -> dict:
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    for _ in range(5):
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(2)
    raise RuntimeError("Request failed")


def api_get(endpoint, game_id, api_key, token=None, params=None):
    query = {}
    if not token:
        query["api_key"] = api_key
    if params:
        query.update(params)
    qs = f"?{urlencode(query)}" if query else ""
    url = f"{base_url(game_id)}{endpoint}{qs}"
    return make_request(url, token)


def get_all_pages(endpoint, game_id, api_key, token=None):
    results = []
    offset = 0
    while True:
        data = api_get(endpoint, game_id, api_key, token, {"_limit": 100, "_offset": offset})
        items = data.get("data", [])
        results.extend(items)
        count = len(items)
        total = data.get("result_total", count)
        offset += count
        if offset >= total or count == 0:
            break
    return results


def search_games(query: str, api_key: str):
    """Search for games on mod.io by name."""
    try:
        params = urlencode({"api_key": api_key, "_q": query, "_limit": 8})
        url = f"https://api.mod.io/v1/games?{params}"
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("data", [])
    except Exception:
        return []


def get_collection_mods(game_id, collection_id, api_key, token):
    return get_all_pages(f"/games/{game_id}/collections/{collection_id}/mods", game_id, api_key, token)


def get_mod_file(game_id, mod_id, api_key, token):
    data = api_get(
        f"/games/{game_id}/mods/{mod_id}/files",
        game_id, api_key, token,
        {"_limit": 1, "_sort": "-date_added"},
    )
    files = data.get("data", [])
    return files[0] if files else None

# ─────────────────────────────────────────────
#  Game ID picker with live search suggestions
# ─────────────────────────────────────────────

def pick_game_id(api_key: str) -> int:
    """
    Ask the user for a game name or numeric ID.
    Shows live search suggestions while they type.
    Returns the chosen game_id as int.
    """
    print(f"\n  {bold('Search for a game')}")
    print(f"  {dim('Tip: type a name to get suggestions, or enter a Game ID directly.')}\n")

    last_query = None
    suggestions = []

    while True:
        try:
            raw = input(f"  {cyan('?')} {bold('Game name or ID')}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{yellow('Cancelled.')}")
            sys.exit(0)

        if not raw:
            print(f"  {yellow('Please enter a name or ID.')}")
            continue

        # Numeric → treat as direct ID
        if raw.isdigit():
            return int(raw)

        # Search suggestions
        if raw != last_query:
            print(f"  {dim('Searching...')}", end="\r", flush=True)
            suggestions = search_games(raw, api_key)
            last_query = raw
            clear_line()

        if not suggestions:
            print(f"  {yellow('No games found. Try a different term or enter the ID directly.')}")
            continue

        # Show results
        print(f"\n  {bold('Games found:')}")
        for idx, game in enumerate(suggestions, 1):
            name = game.get("name", "?")
            gid  = game.get("id", "?")
            summary = game.get("summary", "")[:60]
            summary = f" – {dim(summary)}" if summary else ""
            print(f"  {cyan(str(idx))}) {bold(name)} {dim(f'[ID: {gid}]')}{summary}")

        print(f"  {cyan('0')}) {dim('Search again')}\n")

        while True:
            try:
                choice = input(f"  {cyan('?')} {bold('Your choice (number)')}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n\n{yellow('Cancelled.')}")
                sys.exit(0)

            if choice == "0":
                last_query = None  # force new search
                break

            if choice.isdigit():
                n = int(choice)
                if 1 <= n <= len(suggestions):
                    chosen = suggestions[n - 1]
                    gid_str = chosen['id']
                    print(f"  {green('✓')} {bold(chosen['name'])} selected {dim(f'(ID: {gid_str})')}\n")
                    return chosen["id"]

            print(f"  {yellow('Invalid choice.')}")

# ─────────────────────────────────────────────
#  Download helpers
# ─────────────────────────────────────────────

def progress_bar(current, total, length=30):
    if total == 0:
        return "░" * length + "  ?.?%"
    ratio = min(current / total, 1.0)
    filled = int(ratio * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar} {ratio*100:5.1f}%"


def fmt_bytes(n):
    if n < 1024:
        return f"{n} B"
    elif n < 1024 ** 2:
        return f"{n/1024:.1f} KB"
    elif n < 1024 ** 3:
        return f"{n/1024**2:.1f} MB"
    else:
        return f"{n/1024**3:.2f} GB"


def extract_zip(zip_path: Path, dest: Path):
    with zipfile.ZipFile(zip_path, "r") as z:
        members = z.namelist()
        top_level = {m.split("/")[0] for m in members if "/" in m}
        if len(top_level) == 1:
            root = list(top_level)[0]
            for member in members:
                if member.endswith("/"):
                    continue
                rel = Path(member).relative_to(root)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())
        else:
            z.extractall(dest)
    zip_path.unlink()


def download_file(url, dest, filename, mod_index, total_mods, mod_name):
    dest.mkdir(parents=True, exist_ok=True)
    filepath = dest / filename
    retries_used = 0

    name_short = (mod_name[:30] + "…") if len(mod_name) > 30 else f"{mod_name:<31}"

    def render(bar, done_str, size_str, icon):
        retry_str = f" ⚠{retries_used}" if retries_used else ""
        line = (
            f"  {icon} [{mod_index:>2}/{total_mods}] "
            f"{bold(name_short)}  "
            f"{cyan(bar)}  "
            f"{dim(done_str + '/' + size_str)}"
            f"{yellow(retry_str)}"
            f"          "   # trailing spaces to wipe leftover chars
        )
        print(f"\r{line}", end="", flush=True)

    for attempt in range(5):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=30) as resp, open(filepath, "wb") as f:
                total      = int(resp.headers.get("Content-Length", 0))
                size_str   = fmt_bytes(total) if total else "?"
                downloaded = 0

                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    render(
                        bar      = progress_bar(downloaded, total, length=20),
                        done_str = fmt_bytes(downloaded),
                        size_str = size_str,
                        icon     = cyan(next(SPINNER)),
                    )

            # Fertig – Zeile grün abschließen, dann newline für nächsten Mod
            render(
                bar      = progress_bar(1, 1, length=20),
                done_str = fmt_bytes(downloaded),
                size_str = fmt_bytes(total) if total else "?",
                icon     = green("✓"),
            )

            if filepath.suffix == ".zip":
                print(f"\r  {dim('⤷')} [{mod_index:>2}/{total_mods}] {dim(name_short)}  Extracting…          ", end="", flush=True)
                extract_zip(filepath, dest)
                render(
                    bar      = progress_bar(1, 1, length=20),
                    done_str = fmt_bytes(downloaded),
                    size_str = fmt_bytes(total) if total else "?",
                    icon     = green("✓"),
                )

            print()  # new line for next mod
            return True, retries_used

        except Exception:
            retries_used += 1
            if filepath.exists():
                filepath.unlink()
            render(
                bar="░" * 20, done_str="–", size_str="?",
                icon=yellow("⚠"),
            )
            time.sleep(1)

    print()
    return False, retries_used


def sanitize(name: str) -> str:
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in name).strip()

# ─────────────────────────────────────────────
#  Interactive setup wizard
# ─────────────────────────────────────────────

def run_wizard():
    print_header()
    print(f"  Welcome! Answer a few quick questions and we'll get started.\n")

    # ── API Key ──────────────────────────────
    print(f"  {bold('Step 1/4 – API Key')}")
    print(f"  {dim('Find your API key at https://mod.io/me/access under \"API Access\".')}\n")
    api_key = ""
    while not api_key:
        api_key = ask("Your mod.io API Key")
        if not api_key:
            print(f"  {yellow('API key cannot be empty.')}")

    # ── OAuth Token (optional) ────────────────
    print(f"\n  {bold('Step 2/4 – OAuth Token (optional)')}")
    print(f"  {dim('Only needed for private collections. You can skip this.')}\n")

    token = None
    if ask_yes_no("Use an OAuth token for private collections?", default=False):
        token = ask("Your OAuth token", password=True)
        if not token:
            token = None
            print(f"  {yellow('No token entered – skipping.')}")

    # ── Game ID ───────────────────────────────
    print(f"\n  {bold('Step 3/4 – Select a game')}")
    game_id = pick_game_id(api_key)

    # ── Collection ID ─────────────────────────
    print(f"  {bold('Step 4/4 – Collection ID')}")
    print(f"  {dim('The collection ID is found in the collection page on mod.io.')}\n")

    collection_id = None
    while collection_id is None:
        raw = ask("Collection ID (number)")
        if raw.isdigit():
            collection_id = int(raw)
        else:
            print(f"  {yellow('Please enter a valid number.')}")

    # ── Output directory ──────────────────────
    print()
    default_out = "./mods_download"
    raw_out = ask(f"Download folder {dim(f'[default: {default_out}]')}")
    output_dir = Path(raw_out if raw_out else default_out)

    # ── Summary ───────────────────────────────
    print(f"\n  {bold('─── Summary ────────────────────────────────')}")
    print(f"  Game ID    : {cyan(str(game_id))}")
    print(f"  Collection : {cyan(str(collection_id))}")
    print(f"  Token      : {green('Yes') if token else dim('No')}")
    print(f"  Save path  : {cyan(str(output_dir.resolve()))}")
    print(f"  {'─'*43}\n")

    if not ask_yes_no("Everything correct? Start downloading?", default=True):
        print(f"\n{yellow('Cancelled.')}")

        sys.exit(0)

    return api_key, token, game_id, collection_id, output_dir

# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    api_key, token, game_id, collection_id, output_dir = run_wizard()

    print(f"\n  {dim('Fetching mod list…')}")
    try:
        mods = get_collection_mods(game_id, collection_id, api_key, token)
    except Exception as e:
        print(f"\n  {red('Error loading collection:')} {e}")
        sys.exit(1)

    if not mods:
        print(f"  {yellow('No mods found in this collection.')}")
        sys.exit(0)

    print(f"  {green('✓')} {bold(str(len(mods)))} mods found. Starting download…")
    print(f"  {dim('─'*45)}")

    failed = []
    skipped = []
    retry_stats = {}

    for i, mod in enumerate(mods, 1):
        mod_id   = mod["id"]
        mod_name = sanitize(mod.get("name", f"mod_{mod_id}"))

        try:
            file_info = get_mod_file(game_id, mod_id, api_key, token)
        except Exception:
            failed.append(mod_name)
            continue

        if not file_info:
            skipped.append(mod_name)
            continue

        url      = file_info.get("download", {}).get("binary_url")
        filename = file_info.get("filename", f"{mod_id}.zip")

        if not url:
            skipped.append(mod_name)
            continue

        success, retries = download_file(url, output_dir / mod_name, filename, i, len(mods), mod_name)
        retry_stats[mod_name] = retries

        if not success:
            failed.append(mod_name)

    # ── Final report ──────────────────────────
    print(f"\n\n  {bold(green('═══ Download complete! ═══'))}\n")
    print(f"  {green('✓')} Succeeded : {len(mods) - len(failed) - len(skipped)}")
    print(f"  {yellow('⚠')} Skipped   : {len(skipped)}")
    print(f"  {red('✗')} Failed    : {len(failed)}")

    needs_retry = {m: r for m, r in retry_stats.items() if r > 0}
    if needs_retry:
        print(f"\n  {bold('Mods with retries:')}")
        for mod, r in needs_retry.items():
            print(f"    {dim('–')} {mod}: {r}×")

    if failed:
        print(f"\n  {bold(red('Failed mods:'))}")
        for m in failed:
            print(f"    {dim('–')} {m}")

    if skipped:
        print(f"\n  {bold(yellow('Skipped mods (no download available):'))}")
        for m in skipped:
            print(f"    {dim('–')} {m}")

    print(f"\n  {bold('Saved to:')} {cyan(str(output_dir.resolve()))}\n")


if __name__ == "__main__":
    main()
