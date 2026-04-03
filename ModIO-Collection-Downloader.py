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


def search_collections(game_id: int, query: str, api_key: str, token: str = None):
    """Search collections for a game by name."""
    try:
        params = {"_q": query, "_limit": 8}
        data = api_get(f"/games/{game_id}/collections", game_id, api_key, token, params)
        return data.get("data", [])
    except Exception:
        return []


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


def pick_collection(game_id: int, api_key: str, token: str = None) -> tuple:
    """
    Interactive collection picker.
    Type a name for search suggestions, or enter a numeric ID directly.
    Returns (collection_id, collection_name).
    """
    print(f"\n  {bold('Search for a collection')}")
    print(f"  {dim('Type a name to get suggestions, or enter a Collection ID directly.')}\n")

    last_query = None
    suggestions = []

    while True:
        try:
            raw = input(f"  {cyan('?')} {bold('Collection name or ID')}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{yellow('Cancelled.')}")
            sys.exit(0)

        if not raw:
            print(f"  {yellow('Please enter a name or ID.')}")
            continue

        if raw.isdigit():
            return int(raw), f"collection-{raw}"

        if raw != last_query:
            print(f"  {dim('Searching...')}", end="\r", flush=True)
            suggestions = search_collections(game_id, raw, api_key, token)
            last_query = raw
            clear_line()

        if not suggestions:
            print(f"  {yellow('No collections found. Try a different term or enter the ID directly.')}")
            continue

        print(f"\n  {bold('Collections found:')}")
        for idx, col in enumerate(suggestions, 1):
            name    = col.get("name", "?")
            cid     = col.get("id", "?")
            summary = col.get("summary", "")[:60]
            summary = f" – {dim(summary)}" if summary else ""
            mod_count = col.get("mod_count", "?")
            print(f"  {cyan(str(idx))}) {bold(name)} {dim(f'[ID: {cid}]')} {dim(f'({mod_count} mods)')}{summary}")

        print(f"  {cyan('0')}) {dim('Search again')}\n")

        while True:
            try:
                choice = input(f"  {cyan('?')} {bold('Your choice (number)')}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n\n{yellow('Cancelled.')}")
                sys.exit(0)

            if choice == "0":
                last_query = None
                break

            if choice.isdigit():
                n = int(choice)
                if 1 <= n <= len(suggestions):
                    chosen  = suggestions[n - 1]
                    cid_str = chosen["id"]
                    cname   = sanitize(chosen.get("name", f"collection-{cid_str}"))
                    print(f"  {green('✓')} {bold(chosen['name'])} selected {dim(f'(ID: {cid_str})')}\n")
                    return chosen["id"], cname

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
        # Collect all top-level names (folders and files)
        top_level = {m.split("/")[0] for m in members}
        # Only strip the root folder if ALL content is under exactly one folder
        folders_with_slash = {m.split("/")[0] for m in members if "/" in m}
        root_files = [m for m in members if "/" not in m and not m.endswith("/")]

        if len(folders_with_slash) == 1 and not root_files:
            root = list(folders_with_slash)[0]
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


ANNO_117_ID = 11358  # Anno 117 game ID on mod.io
SCRIPT_DIR  = Path(__file__).resolve().parent
CREDS_FILE  = SCRIPT_DIR / "credentials.json"

# ─────────────────────────────────────────────
#  Credentials persistence
# ─────────────────────────────────────────────

def load_credentials() -> dict:
    if CREDS_FILE.exists():
        try:
            return json.loads(CREDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_credentials(data: dict):
    try:
        CREDS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  {yellow(f'Could not save credentials: {e}')}")

# ─────────────────────────────────────────────
#  Anno 117 collection bundler
# ─────────────────────────────────────────────
def read_mod_data(file_path: Path) -> dict:
    """Liest ModID und enthaltene Bundle-IDs aus einer modinfo.json."""
    data = {"id": None, "sub_ids": []}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            data["id"] = content.get("ModID")

            # Prüfen, ob diese Mod selbst schon andere Mods bündelt
            dev = content.get("Development", {})
            bundle = dev.get("Bundle", [])
            if isinstance(bundle, list):
                data["sub_ids"] = bundle
    except Exception:
        # Falls json.load fehlschlägt (z.B. wegen Kommentaren in .jsonc),
        # nutzen wir einen Fallback-Regex für die ModID
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = f.read()
                mid = re.search(r'"ModID"\s*:\s*"([^"]+)"', raw)
                if mid: data["id"] = mid.group(1)
        except: pass
    return data

def find_all_mod_ids_in_folder(folder: Path) -> tuple[set, set]:
    """
    Findet alle ModIDs und alle IDs, die bereits in Unter-Bundles stecken.
    Returns: (set_aller_ids, set_der_sub_ids)
    """
    all_ids = set()
    already_bundled_elsewhere = set()

    for p in folder.rglob("modinfo.json*"):
        if p.is_file():
            mod_data = read_mod_data(p)
            if mod_data["id"]:
                all_ids.add(mod_data["id"])
            if mod_data["sub_ids"]:
                for sid in mod_data["sub_ids"]:
                    already_bundled_elsewhere.add(sid)

    return all_ids, already_bundled_elsewhere

def bundle_as_collection(output_dir: Path, collection_name: str, collection_id: int, succeeded_mods: list[str]):
    import shutil
    print(f"\n  {bold('─── Bundling as Anno 117 collection mod ───')}")

    display_name = ask(f"Bundle display name {dim(f'[default: {collection_name}]')}") or collection_name
    creator = ask(f"Creator name {dim('[default: Unknown]')}") or "Unknown"

    bundle_dir = output_dir / sanitize(display_name)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verschieben
    for mod_name in succeeded_mods:
        src = output_dir / mod_name
        dst = bundle_dir / mod_name
        if src.exists() and src.resolve() != bundle_dir.resolve():
            try:
                if dst.exists(): shutil.rmtree(dst)
                shutil.move(str(src), str(dst))
            except Exception as e:
                print(f"  {red('✗')} Failed to move {mod_name}: {e}")

    # 2. IDs sammeln und Dubletten durch Verschachtelung verhindern
    final_ids = set()
    all_found_sub_ids = set()

    for mod_name in succeeded_mods:
        mod_path = bundle_dir / mod_name
        if mod_path.is_dir():
            found_ids, sub_ids = find_all_mod_ids_in_folder(mod_path)
            final_ids.update(found_ids)
            all_found_sub_ids.update(sub_ids)

    # 3. "Aufräumen": Entferne IDs, die bereits in einer anderen Mod gebündelt sind
    # So verhindern wir, dass eine ID doppelt registriert wird.
    clean_bundle_list = [mid for mid in final_ids if mid not in all_found_sub_ids]

    if not clean_bundle_list:
        print(f"  {red('✗')} No valid mod IDs found – bundle aborted.")
        return

    # 4. JSON Erstellung
    slug = re.sub(r"-+", "-", "".join(c if c.isalnum() or c == "-" else "-" for c in display_name.lower()).strip("-"))
    mod_id_slug = f"collection-{slug}-{collection_id}"

    modinfo = {
        "ModID": mod_id_slug,
        "Version": "1.0.0",
        "Anno": 8,
        "Difficulty": "normal",
        "ModName": { "English": display_name },
        "Category": { "English": "Collection" },
        "CreatorName": creator,
        "Development": {
            "Dependencies": [],
            "DeployPath": "${annoMods}/${modName}",
            "Bundle": sorted(clean_bundle_list)
        }
    }

    with open(bundle_dir / "modinfo.json", "w", encoding="utf-8") as f:
        json.dump(modinfo, f, indent=2, ensure_ascii=False)

    print(f"\n  {bold(green('═══ Bundle created! ═══'))}\n")
    print(f"  {green('✓')} Bundle folder  : {cyan(str(bundle_dir.resolve()))}")
    print(f"  {dim('–')} ModID          : {mod_id_slug}")
    print(f"  {dim('–')} Unique IDs     : {len(clean_bundle_list)}")
    if all_found_sub_ids:
        print(f"  {dim('–')} Sub-IDs hidden : {len(all_found_sub_ids)} (already in sub-bundles)")


def sanitize(name: str) -> str:
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in name).strip()

# ─────────────────────────────────────────────
#  Mod search (single mod picker)
# ─────────────────────────────────────────────

def search_mods(query: str, game_id: int, api_key: str):
    """Search for mods in a game by name."""
    try:
        params = urlencode({"api_key": api_key, "_q": query, "_limit": 8})
        url = f"{base_url(game_id)}/mods?{params}"
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("data", [])
    except Exception:
        return []


def get_mod_name_by_id(mod_id, game_id, api_key):
    """Holt den echten Namen eines Mods via ID von der API."""
    # Wir nutzen die bereits etablierte Subdomain-Logik
    url = f"https://g-{game_id}.modapi.io/v1/games/{game_id}/mods/{mod_id}"
    try:
        resp = requests.get(url, params={"api_key": api_key}, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("name")
    except:
        pass
    return f"mod_{mod_id}" # Fallback, falls API nicht antwortet

def pick_mod(game_id: int, api_key: str, token: str):
    """Interactive mod search & picker. Returns (mod_id, mod_name)."""
    print(f"\n  {bold('Search for a mod')}")
    print(f"  {dim('Type a mod name to get suggestions, or enter a Mod ID directly.')}\n")

    last_query = None
    suggestions = []

    while True:
        try:
            raw = input(f"  {cyan('?')} {bold('Mod name or ID')}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{yellow('Cancelled.')}")
            sys.exit(0)

        if not raw:
            continue

        # FALL 1: User gibt direkt eine numerische ID ein
        if raw.isdigit():
            mod_id = int(raw)
            print(f"  {dim('Fetching mod details...')}", end="\r", flush=True)
            # Hier holen wir uns jetzt den echten Namen!
            real_name = get_mod_name_by_id(mod_id, game_id, api_key)
            clear_line()
            print(f"  {green('✓')} {bold(real_name)} selected {dim(f'(ID: {mod_id})')}\n")
            return mod_id, sanitize(real_name)

        # FALL 2: User gibt einen Suchbegriff ein
        if raw != last_query:
            print(f"  {dim('Searching...')}", end="\r", flush=True)
            suggestions = search_mods(raw, game_id, api_key)
            last_query = raw
            clear_line()

        if not suggestions:
            print(f"  {yellow('No mods found. Try a different term or enter the ID directly.')}")
            continue

        # Anzeige der Suchergebnisse
        print(f"\n  {bold('Mods found:')}")
        for idx, mod in enumerate(suggestions, 1):
            name    = mod.get("name", "?")
            mid     = mod.get("id", "?")
            summary = mod.get("summary", "")[:60]
            summary = f" – {dim(summary)}" if summary else ""
            print(f"  {cyan(str(idx))}) {bold(name)} {dim(f'[ID: {mid}]')}{summary}")

        print(f"  {cyan('0')}) {dim('Search again')}\n")

        while True:
            try:
                choice = input(f"  {cyan('?')} {bold('Your choice (number)')}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n\n{yellow('Cancelled.')}")
                sys.exit(0)

            if choice == "0":
                break

            if choice.isdigit():
                n = int(choice)
                if 1 <= n <= len(suggestions):
                    chosen  = suggestions[n - 1]
                    mid_val = chosen["id"]
                    mod_name = chosen.get("name", f"mod_{mid_val}")
                    print(f"  {green('✓')} {bold(mod_name)} selected {dim(f'(ID: {mid_val})')}\n")
                    # Hier geben wir den echten Namen aus dem API-Objekt zurück
                    return mid_val, sanitize(mod_name)

            print(f"  {yellow('Invalid choice.')}")

# ─────────────────────────────────────────────
#  Shared wizard helpers
# ─────────────────────────────────────────────

def ask_mode() -> str:
    """Ask what the user wants to do. Returns 'collection', 'mod', or 'bundle'."""
    print(f"  {bold('What do you want to do?')}\n")
    print(f"  {cyan('1')}) {bold('Collection Download')}  {dim('– download all mods from a mod.io collection')}")
#    print(f"  {cyan('2')}) {bold('Mod Download')}         {dim('– search and download a single mod')}")
    print(f"  {cyan('2')}) {bold('Anno Mod Bundle')}      {dim('– bundle already downloaded mods into a collection mod')}\n")

    while True:
        try:
            choice = input(f"  {cyan('?')} {bold('Your choice (1 or 2)')}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{yellow('Cancelled.')}")
            sys.exit(0)

        if choice == "1": return "collection"
#        if choice == "2": return "mod"
        if choice == "2": return "bundle"
        print(f"  {yellow('Please enter 1 or 2.')}")


def ask_credentials(need_token=True) -> tuple:
    """Ask for API key and optionally OAuth token, with save/load from credentials.json."""
    creds = load_credentials()

    # ── API Key ───────────────────────────────
    print(f"\n  {bold('API Key')}")
    print(f"  {dim('Find your API key at https://mod.io/me/access under \"API Access\".')}\n")

    saved_key = creds.get("api_key")
    if saved_key:
        print(f"  {green('✓')} Saved API key found: {dim(saved_key[:6] + '…' + saved_key[-4:])}")
        if ask_yes_no("Use saved API key?", default=True):
            api_key = saved_key
        else:
            api_key = ""
            while not api_key:
                api_key = ask("Your mod.io API Key")
                if not api_key:
                    print(f"  {yellow('API key cannot be empty.')}")
            if ask_yes_no("Save this API key for next time?", default=True):
                creds["api_key"] = api_key
                save_credentials(creds)
                print(f"  {green('✓')} API key saved.")
    else:
        api_key = ""
        while not api_key:
            api_key = ask("Your mod.io API Key")
            if not api_key:
                print(f"  {yellow('API key cannot be empty.')}")
        if ask_yes_no("Save this API key for next time?", default=True):
            creds["api_key"] = api_key
            save_credentials(creds)
            print(f"  {green('✓')} API key saved.")

    # ── OAuth Token ───────────────────────────
    token = None
    if need_token:
        print(f"\n  {bold('OAuth Token')} {dim('(optional)')}")
        print(f"  {dim('Only needed for private collections. Press Enter to skip.')}\n")

        saved_token = creds.get("token")
        if saved_token:
            print(f"  {green('✓')} Saved token found: {dim(saved_token[:6] + '…' + saved_token[-4:])}")
            if ask_yes_no("Use saved OAuth token?", default=True):
                token = saved_token
            else:
                if ask_yes_no("Enter a new OAuth token?", default=False):
                    token = ask("Your OAuth token", password=True)
                    if token:
                        if ask_yes_no("Save this token for next time?", default=True):
                            creds["token"] = token
                            save_credentials(creds)
                            print(f"  {green('✓')} Token saved.")
                    else:
                        print(f"  {yellow('No token entered – skipping.')}")
        else:
            if ask_yes_no("Use an OAuth token for private collections?", default=False):
                token = ask("Your OAuth token", password=True)
                if token:
                    if ask_yes_no("Save this token for next time?", default=True):
                        creds["token"] = token
                        save_credentials(creds)
                        print(f"  {green('✓')} Token saved.")
                else:
                    print(f"  {yellow('No token entered – skipping.')}")

    return api_key, token

# ─────────────────────────────────────────────
#  Mode wizards
# ─────────────────────────────────────────────

def wizard_collection():
    """Full wizard for collection download. Returns all needed params."""

    print(f"\n  {bold('── Collection Download ──────────────────────')}\n")

    api_key, token = ask_credentials()

    print(f"\n  {bold('Select a game')}")
    game_id = pick_game_id(api_key)

    print(f"  {bold('Select a collection')}")
    collection_id, collection_name = pick_collection(game_id, api_key, token)

    print()
    default_out = "./mods_download"
    raw_out = ask(f"Download folder {dim(f'[default: {default_out}]')}")
    output_dir = Path(raw_out if raw_out else default_out)

    # Anno 117 bundle option — ask BEFORE summary
    bundle = False
    if game_id == ANNO_117_ID:
        print(f"\n  {bold('Anno 117 detected!')}")
        print(f"  {dim('Anno 117 does not support installing collections natively.')}")
        print(f"  {dim('You can bundle all mods into a single collection mod after downloading.')}\n")
        bundle = ask_yes_no("Bundle all mods as a collection mod for Anno 117?", default=True)

    print(f"\n  {bold('─── Summary ────────────────────────────────')}")
    print(f"  Mode       : {cyan('Collection Download')}")
    print(f"  Game ID    : {cyan(str(game_id))}")
    print(f"  Collection : {cyan(collection_name)} {dim(f'(ID: {collection_id})')}")
    print(f"  Token      : {green('Yes') if token else dim('No')}")
    print(f"  Bundle     : {green('Yes') if bundle else dim('No')}")
    print(f"  Save path  : {cyan(str(output_dir.resolve()))}")
    print(f"  {'─'*43}\n")

    if not ask_yes_no("Everything correct? Start downloading?", default=True):
        print(f"\n{yellow('Cancelled.')}")
        sys.exit(0)

    return api_key, token, game_id, collection_id, collection_name, output_dir, bundle


def wizard_mod():
    """Wizard for single mod download."""

    print(f"\n  {bold('── Mod Download ─────────────────────────────')}\n")

    api_key, token = ask_credentials()

    print(f"\n  {bold('Select a game')}")
    game_id = pick_game_id(api_key)

    mod_id, mod_name = pick_mod(game_id, api_key, token)

    print()
    default_out = "./mods_download"
    raw_out = ask(f"Download folder {dim(f'[default: {default_out}]')}")
    output_dir = Path(raw_out if raw_out else default_out)

    print(f"\n  {bold('─── Summary ────────────────────────────────')}")
    print(f"  Mode      : {cyan('Mod Download')}")
    print(f"  Game ID   : {cyan(str(game_id))}")
    print(f"  Mod       : {cyan(mod_name)} {dim(f'(ID: {mod_id})')}")
    print(f"  Token     : {green('Yes') if token else dim('No')}")
    print(f"  Save path : {cyan(str(output_dir.resolve()))}")
    print(f"  {'─'*43}\n")

    if not ask_yes_no("Everything correct? Start downloading?", default=True):
        print(f"\n{yellow('Cancelled.')}")
        sys.exit(0)

    return api_key, token, game_id, mod_id, mod_name, output_dir


def wizard_bundle():
    """Wizard for bundling already-downloaded mods."""

    print(f"\n  {bold('── Anno Mod Bundle ──────────────────────────')}\n")
    print(f"  {dim('Point to a folder containing already-downloaded Anno 117 mods.')}\n")

    while True:
        raw = ask("Path to your mods folder")
        mods_dir = Path(raw).expanduser()
        if mods_dir.is_dir():
            break
        print(f"  {yellow('Folder not found. Please enter a valid path.')}")

    # Discover mod sub-folders
    found = []
    no_modinfo = []
    for entry in sorted(mods_dir.iterdir()):
        if entry.is_dir():
            mod_id = find_mod_id(entry)
            if mod_id:
                found.append((entry.name, mod_id))
            else:
                no_modinfo.append(entry.name)

    if not found and not no_modinfo:
        print(f"  {red('✗')} No mod folders found in that folder.")
        sys.exit(1)

    if found:
        print(f"\n  {green('✓')} Found {bold(str(len(found)))} mod(s) with modinfo.json:\n")
        for name, mid in found:
            print(f"    {dim('–')} {name}  {dim(f'[ModID: {mid}]')}")

    if no_modinfo:
        print(f"\n  {yellow('⚠')} {len(no_modinfo)} folder(s) without modinfo.json – will be skipped in bundle:")
        for name in no_modinfo:
            print(f"    {dim('–')} {name}")

    if not found:
        print(f"\n  {red('✗')} No bundleable mods found.")
        sys.exit(1)

    print()
    display_name = ask("Bundle display name")
    while not display_name:
        print(f"  {yellow('Name cannot be empty.')}")
        display_name = ask("Bundle display name")

    creator = ask(f"Creator name {dim('[default: Unknown]')}")
    if not creator:
        creator = "Unknown"

    print(f"\n  {bold('─── Summary ────────────────────────────────')}")
    print(f"  Mode        : {cyan('Anno Mod Bundle')}")
    print(f"  Mods folder : {cyan(str(mods_dir.resolve()))}")
    print(f"  Mods found  : {cyan(str(len(found)))}")
    print(f"  Bundle name : {cyan(display_name)}")
    print(f"  Creator     : {cyan(creator)}")
    print(f"  {'─'*43}\n")

    if not ask_yes_no("Everything correct? Create bundle?", default=True):
        print(f"\n{yellow('Cancelled.')}")
        sys.exit(0)

    return mods_dir, found, display_name, creator

# ─────────────────────────────────────────────
#  Mode runners
# ─────────────────────────────────────────────

def run_collection():
    api_key, token, game_id, collection_id, collection_name, output_dir, bundle = wizard_collection()

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

    failed, skipped, retry_stats, succeeded = [], [], {}, []

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
        (succeeded if success else failed).append(mod_name)

    # Report
    print(f"\n\n  {bold(green('═══ Download complete! ═══'))}\n")
    print(f"  {green('✓')} Succeeded : {len(succeeded)}")
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

    if bundle and succeeded:
        bundle_as_collection(output_dir, collection_name, collection_id, succeeded)
        print()


def run_mod():
    api_key, token, game_id, mod_id, mod_name, output_dir = wizard_mod()

    print(f"\n  {dim('Fetching mod info…')}")
    try:
        file_info = get_mod_file(game_id, mod_id, api_key, token)
    except Exception as e:
        print(f"\n  {red('Error fetching mod:')} {e}")
        sys.exit(1)

    if not file_info:
        print(f"  {yellow('No downloadable file found for this mod.')}")
        sys.exit(0)

    url      = file_info.get("download", {}).get("binary_url")
    filename = file_info.get("filename", f"{mod_name}.zip")

    if not url:
        print(f"  {yellow('No download URL available for this mod.')}")
        sys.exit(0)

    print(f"  {green('✓')} File found. Starting download…")
    print(f"  {dim('─'*45)}")

    success, retries = download_file(url, output_dir / mod_name, filename, 1, 1, mod_name)

    print(f"\n\n  {bold(green('═══ Download complete! ═══'))}\n")
    if success:
        print(f"  {green('✓')} {mod_name} downloaded successfully")
        if retries:
            print(f"  {dim('–')} Retries used: {retries}")
    else:
        print(f"  {red('✗')} Download failed after 5 attempts.")

    print(f"\n  {bold('Saved to:')} {cyan(str(output_dir.resolve()))}\n")


def run_bundle():
    mods_dir, found, display_name, creator = wizard_bundle()

    # Build bundle entries using folder names (Anno 117 expects folder names, not ModIDs)
    bundle_entries = [f"./{mod_name}" for mod_name, _ in found]

    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in display_name.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    mod_id_slug = f"collection-{slug}"

    modinfo = {
        "ModID": mod_id_slug,
        "Version": "1.0.0",
        "Anno": 8,
        "Difficulty": "normal",
        "ModName": {"English": display_name},
        "Category": {"English": "Collection"},
        "CreatorName": creator,
        "CreatorContact": "",
        "Development": {
            "Dependencies": [],
            "DeployPath": "${annoMods}/${modName}",
            "Bundle": bundle_entries
        }
    }

    bundle_dir = mods_dir / sanitize(display_name)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Move mod folders into the bundle dir
    import shutil
    moved, move_failed = [], []
    for mod_name, _ in found:
        src = mods_dir / mod_name
        dst = bundle_dir / mod_name
        if src.exists() and src.resolve() != bundle_dir.resolve():
            try:
                shutil.move(str(src), str(dst))
                moved.append(mod_name)
            except Exception:
                move_failed.append(mod_name)

    if move_failed:
        print(f"  {yellow('⚠')} Could not move {len(move_failed)} folder(s):")
        for m in move_failed:
            print(f"    {dim('–')} {m}")

    modinfo_path = bundle_dir / "modinfo.json"
    with open(modinfo_path, "w", encoding="utf-8") as f:
        json.dump(modinfo, f, indent=2, ensure_ascii=False)

    print(f"\n  {bold(green('═══ Bundle created! ═══'))}\n")
    print(f"  {green('✓')} Bundle folder  : {cyan(str(bundle_dir.resolve()))}")
    print(f"  {dim('–')} ModID          : {mod_id_slug}")
    print(f"  {dim('–')} Mods included  : {len(moved)}")
    print(f"  {dim('–')} modinfo.json written\n")

# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    print_header()
    print(f"  Welcome! What would you like to do?\n")

    mode = ask_mode()

    if mode == "collection":
        run_collection()
    elif mode == "mod":
        run_mod()
    elif mode == "bundle":
        run_bundle()


if __name__ == "__main__":
    main()
