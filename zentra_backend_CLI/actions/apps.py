import os
import platform
import shutil
import subprocess
from pathlib import Path

from config import BASE_FOLDER, PSUTIL_AVAILABLE, WINREG_AVAILABLE
from logger import log

if PSUTIL_AVAILABLE:
    import psutil

if WINREG_AVAILABLE:
    import winreg


_APP_ALIASES: dict[str, str] = {
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge", "microsoft edge": "msedge",
    "brave": "brave", "opera": "opera", "opera gx": "opera",
    "vivaldi": "vivaldi", "tor": "tor browser",
    "steam": "steam",
    "epic": "epicgameslauncher", "epic games": "epicgameslauncher",
    "epic games launcher": "epicgameslauncher",
    "gog": "goggalaxy", "gog galaxy": "goggalaxy",
    "origin": "origin", "ea app": "eadesktop",
    "ubisoft": "ubisoftconnect", "uplay": "ubisoftconnect",
    "ubisoft connect": "ubisoftconnect",
    "battle.net": "battle.net", "battlenet": "battle.net",
    "riot": "riotclientservices", "riot games": "riotclientservices",
    "league": "riotclientservices",
    "minecraft": "minecraftlauncher",
    "xbox": "xboxapp", "xbox app": "xboxapp",
    "spotify": "spotify", "vlc": "vlc", "mpv": "mpv", "plex": "plex",
    "obs": "obs64", "obs studio": "obs64",
    "audacity": "audacity", "winamp": "winamp",
    "foobar": "foobar2000", "foobar2000": "foobar2000",
    "discord": "discord", "slack": "slack",
    "teams": "teams", "microsoft teams": "teams",
    "zoom": "zoom", "telegram": "telegram",
    "signal": "signal", "whatsapp": "whatsapp", "skype": "skype",
    "vscode": "code", "visual studio code": "code",
    "vs code": "code", "code": "code",
    "visual studio": "devenv",
    "pycharm": "pycharm64", "intellij": "idea64",
    "webstorm": "webstorm64", "clion": "clion64",
    "rider": "rider64", "datagrip": "datagrip64",
    "android studio": "studio64", "cursor": "cursor",
    "sublime": "sublime_text", "sublime text": "sublime_text",
    "notepad++": "notepad++", "atom": "atom",
    "vim": "vim", "neovim": "nvim",
    "terminal": "wt", "windows terminal": "wt",
    "powershell": "powershell", "cmd": "cmd",
    "command prompt": "cmd", "git bash": "git-bash", "wsl": "wsl",
    "postman": "postman", "insomnia": "insomnia",
    "docker": "docker desktop", "docker desktop": "docker desktop",
    "dbeaver": "dbeaver", "tableplus": "tableplus",
    "notepad": "notepad", "wordpad": "wordpad",
    "word": "winword", "excel": "excel",
    "powerpoint": "powerpnt", "outlook": "outlook",
    "onenote": "onenote", "access": "msaccess",
    "libreoffice": "soffice", "libreoffice writer": "swriter",
    "libreoffice calc": "scalc",
    "notion": "notion", "obsidian": "obsidian", "todoist": "todoist",
    "photoshop": "photoshop", "illustrator": "illustrator",
    "premiere": "premiere", "after effects": "afterfx",
    "lightroom": "lightroom", "gimp": "gimp",
    "inkscape": "inkscape", "blender": "blender",
    "figma": "figma", "davinci": "resolve", "davinci resolve": "resolve",
    "task manager": "taskmgr", "file explorer": "explorer",
    "explorer": "explorer", "calculator": "calc",
    "paint": "mspaint", "snipping tool": "snippingtool",
    "settings": "ms-settings:", "control panel": "control",
    "registry editor": "regedit",
    "device manager": "devmgmt.msc",
    "event viewer": "eventvwr.msc",
    "disk management": "diskmgmt.msc",
}

_WIN_SEARCH_ROOTS: list[str] = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.expandvars(r"%LOCALAPPDATA%"),
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
]

_WIN_KNOWN_PATHS: dict[str, list[str]] = {
    "steam": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Steam\steam.exe"),
    ],
    "epicgameslauncher": [
        r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
        r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\EpicGamesLauncher\Portal\Binaries\Win32\EpicGamesLauncher.exe"),
    ],
    "goggalaxy": [
        r"C:\Program Files (x86)\GOG Galaxy\GalaxyClient.exe",
        r"C:\Program Files\GOG Galaxy\GalaxyClient.exe",
    ],
    "origin": [
        r"C:\Program Files (x86)\Origin\Origin.exe",
        r"C:\Program Files\Origin\Origin.exe",
    ],
    "eadesktop": [
        os.path.expandvars(r"%LOCALAPPDATA%\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe"),
    ],
    "ubisoftconnect": [
        r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
        r"C:\Program Files\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
    ],
    "battle.net": [
        r"C:\Program Files (x86)\Battle.net\Battle.net.exe",
        r"C:\Program Files\Battle.net\Battle.net.exe",
    ],
    "riotclientservices": [
        os.path.expandvars(r"%LOCALAPPDATA%\Riot Games\Riot Client\RiotClientServices.exe"),
    ],
    "discord": [
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"),
    ],
    "spotify": [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
    ],
    "telegram": [
        os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe"),
    ],
    "obs64": [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
    ],
    "postman": [
        os.path.expandvars(r"%LOCALAPPDATA%\Postman\Postman.exe"),
        os.path.expandvars(r"%APPDATA%\Postman\Postman.exe"),
    ],
}


_PROC_ALIASES: dict[str, list[str]] = {
    "chrome":        ["chrome", "chrome.exe", "google chrome", "googlechrome"],
    "firefox":       ["firefox", "firefox.exe"],
    "edge":          ["msedge", "msedge.exe", "microsoft edge"],
    "brave":         ["brave", "brave.exe", "brave-browser"],
    "opera":         ["opera", "opera.exe"],
    "discord":       ["discord", "discord.exe"],
    "spotify":       ["spotify", "spotify.exe"],
    "steam":         ["steam", "steam.exe"],
    "notepad":       ["notepad", "notepad.exe"],
    "notepad++":     ["notepad++", "notepad++.exe"],
    "vscode":        ["code", "code.exe", "visual studio code"],
    "vs code":       ["code", "code.exe"],
    "code":          ["code", "code.exe"],
    "explorer":      ["explorer", "explorer.exe"],
    "obs":           ["obs64", "obs32", "obs.exe", "obs64.exe"],
    "vlc":           ["vlc", "vlc.exe"],
    "slack":         ["slack", "slack.exe"],
    "teams":         ["teams", "teams.exe"],
    "zoom":          ["zoom", "zoom.exe"],
    "telegram":      ["telegram", "telegram.exe", "telegramdesktop"],
    "word":          ["winword", "winword.exe"],
    "excel":         ["excel", "excel.exe"],
    "powerpoint":    ["powerpnt", "powerpnt.exe"],
    "outlook":       ["outlook", "outlook.exe"],
    "photoshop":     ["photoshop", "photoshop.exe"],
    "blender":       ["blender", "blender.exe"],
    "task manager":  ["taskmgr", "taskmgr.exe"],
    "cmd":           ["cmd", "cmd.exe"],
    "powershell":    ["powershell", "powershell.exe", "pwsh", "pwsh.exe"],
    "terminal":      ["wt", "wt.exe", "terminal"],
    "pycharm":       ["pycharm64", "pycharm64.exe", "pycharm"],
    "intellij":      ["idea64", "idea64.exe"],
    "postman":       ["postman", "postman.exe"],
    "docker":        ["docker", "docker desktop", "dockerdesktop"],
}

PROTECTED_PROCESSES = {
    "system", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "lsass.exe", "services.exe", "svchost.exe", "dwm.exe",
    "kernel_task", "launchd", "systemd", "init",
}


def _normalize_proc_name(name: str) -> list[str]:
    name = name.strip().lower()
    base = name.removesuffix(".exe")
    candidates = {name, base}
    if base in _PROC_ALIASES:
        candidates.update(_PROC_ALIASES[base])
    if name in _PROC_ALIASES:
        candidates.update(_PROC_ALIASES[name])
    return list(candidates)


def _find_processes_by_name(name_or_pid: str) -> list:
    if not PSUTIL_AVAILABLE:
        return []
    try:
        pid = int(name_or_pid)
        p   = psutil.Process(pid)
        return [p]
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    candidates = _normalize_proc_name(name_or_pid)
    matches    = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            proc_name = (proc.info.get("name") or "").lower()
            proc_exe  = (proc.info.get("exe")  or "").lower()
            for candidate in candidates:
                if candidate in proc_name or candidate in proc_exe:
                    matches.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return matches


def _registry_lookup_windows(app_name: str) -> str | None:
    if not WINREG_AVAILABLE:
        return None
    search    = app_name.lower().replace(".exe", "")
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    for hive in hives:
        for reg_path in reg_paths:
            try:
                key   = winreg.OpenKey(hive, reg_path)
                count = winreg.QueryInfoKey(key)[0]
            except OSError:
                continue
            for i in range(count):
                try:
                    sub_name = winreg.EnumKey(key, i)
                    sub_key  = winreg.OpenKey(key, sub_name)
                except OSError:
                    continue
                try:
                    display_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                    if search not in display_name.lower():
                        continue
                    for value_name in ("DisplayIcon", "InstallLocation"):
                        try:
                            val, _ = winreg.QueryValueEx(sub_key, value_name)
                            val    = val.split(",")[0].strip().strip('"')
                            if val.lower().endswith(".exe") and Path(val).exists():
                                log.info(f"Registry found: {display_name} -> {val}")
                                return val
                            folder = Path(val)
                            if folder.is_dir():
                                for exe in folder.glob("*.exe"):
                                    return str(exe)
                        except OSError:
                            pass
                except OSError:
                    pass
                finally:
                    sub_key.Close()
            key.Close()
    return None


def _glob_known_path(pattern: str) -> str | None:
    if "*" not in pattern:
        p = Path(pattern)
        return str(p) if p.exists() else None
    parent = Path(pattern).parent
    name   = Path(pattern).name
    try:
        matches = sorted(parent.glob(name), reverse=True)
        return str(matches[0]) if matches else None
    except OSError:
        return None


def _find_app_windows(canonical: str, original: str) -> str | None:
    found = shutil.which(canonical) or shutil.which(original)
    if found:
        return found
    for key in (canonical, original):
        for path_pattern in _WIN_KNOWN_PATHS.get(key, []):
            result = _glob_known_path(path_pattern)
            if result:
                return result
    reg = _registry_lookup_windows(canonical) or _registry_lookup_windows(original)
    if reg:
        return reg
    search_terms = {canonical.lower(), original.lower()}
    search_terms.discard("")
    for root in _WIN_SEARCH_ROOTS:
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        try:
            for sub in root_path.iterdir():
                if not sub.is_dir():
                    continue
                if any(term in sub.name.lower() for term in search_terms):
                    exes = sorted(sub.glob("*.exe"))
                    if exes:
                        log.info(f"Folder scan found: {exes[0]}")
                        return str(exes[0])
        except PermissionError:
            pass
    return None


def _find_app_macos(canonical: str, original: str) -> str | None:
    for name in [original, canonical, original.title(), canonical.title()]:
        try:
            result = subprocess.run(
                ["mdfind", f"kMDItemCFBundleIdentifier == '*{name.lower()}*'"],
                capture_output=True, text=True, timeout=5,
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            if lines:
                return lines[0]
        except Exception:
            pass
    return None


def _find_app_linux(canonical: str, original: str) -> str | None:
    found = shutil.which(canonical) or shutil.which(original)
    if found:
        return found
    desktop_dirs = [
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path.home() / ".local/share/applications",
    ]
    search = {canonical.lower(), original.lower()}
    for d in desktop_dirs:
        if not d.is_dir():
            continue
        for desktop in d.glob("*.desktop"):
            text = desktop.read_text(errors="replace").lower()
            if any(s in text for s in search):
                for line in desktop.read_text(errors="replace").splitlines():
                    if line.startswith("Exec="):
                        return line[5:].split()[0].strip()
    return None


def _platform_launch(target: str, system: str) -> None:
    if system == "Windows":
        os.startfile(target)
    elif system == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen([target])


def handle_open_app(data: dict) -> str:
    app_raw  = data.get("app", "").strip()
    app_path = data.get("app_path", "").strip()
    system   = platform.system()

    if not app_raw and not app_path:
        return "open_app: no app name or path was provided."

    if app_path:
        p = Path(app_path)
        if not p.exists():
            return f"Path not found: `{app_path}`"
        try:
            _platform_launch(str(p), system)
            return f"Opened: `{app_path}`"
        except Exception as exc:
            return f"Could not open `{app_path}`: {exc}"

    app_lower = app_raw.lower().strip()
    canonical = _APP_ALIASES.get(app_lower, app_lower)
    log.info(f"open_app: raw='{app_raw}' -> canonical='{canonical}'")

    if system == "Windows":
        exe = _find_app_windows(canonical, app_lower)
        if exe:
            try:
                _platform_launch(exe, system)
                return f"Launched **{app_raw}**."
            except Exception as exc:
                return f"Found `{exe}` but couldn't launch it: {exc}"
        try:
            os.startfile(canonical)
            return f"Launched **{app_raw}**."
        except Exception:
            pass

    elif system == "Darwin":
        exe = _find_app_macos(canonical, app_lower)
        if exe:
            try:
                subprocess.Popen(["open", exe])
                return f"Launched **{app_raw}**."
            except Exception as exc:
                return f"Found `{exe}` but couldn't launch it: {exc}"
        for name in [app_raw, app_raw.title(), canonical, canonical.title()]:
            try:
                r = subprocess.run(["open", "-a", name], capture_output=True, text=True)
                if r.returncode == 0:
                    return f"Launched **{name}**."
            except Exception:
                pass

    else:
        exe = _find_app_linux(canonical, app_lower)
        if exe:
            try:
                subprocess.Popen([exe])
                return f"Launched **{app_raw}**."
            except Exception as exc:
                return f"Found `{exe}` but couldn't launch it: {exc}"
        try:
            subprocess.Popen(["xdg-open", app_lower])
            return f"Launched **{app_raw}** via xdg-open."
        except Exception:
            pass

    return (
        f"Couldn't find **{app_raw}** on your system.\n"
        f"Try telling me the full path and I'll open it directly."
    )


def handle_close_app(data: dict) -> str:
    if not PSUTIL_AVAILABLE:
        return (
            "`psutil` is not installed — required for close_app.\n"
            "Run: `pip install psutil` then restart ZENTRA."
        )

    app_name = (data.get("app") or data.get("app_path") or "").strip()
    if not app_name:
        return "close_app: no app name or PID provided."

    procs = _find_processes_by_name(app_name)

    if not procs:
        if platform.system() == "Windows":
            exe_name = app_name if app_name.endswith(".exe") else f"{app_name}.exe"
            r = subprocess.run(
                ["taskkill", "/F", "/IM", exe_name],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                return f"Closed **{app_name}** via taskkill."
            r2 = subprocess.run(
                ["taskkill", "/F", "/IM", app_name],
                capture_output=True, text=True,
            )
            if r2.returncode == 0:
                return f"Closed **{app_name}** via taskkill."
        return f"No running process found matching **{app_name}**."

    killed  = []
    failed  = []
    skipped = []

    for proc in procs:
        try:
            pname = proc.name().lower()
            if pname in PROTECTED_PROCESSES:
                skipped.append(f"{proc.name()} (PID {proc.pid}) — system process, skipped")
                continue

            log.info(f"Terminating {proc.name()} (PID {proc.pid})")
            proc.terminate()

            try:
                proc.wait(timeout=3)
                killed.append(f"{proc.name()} (PID {proc.pid})")
            except psutil.TimeoutExpired:
                log.warning(f"Process {proc.name()} didn't exit — killing forcefully")
                proc.kill()
                proc.wait(timeout=2)
                killed.append(f"{proc.name()} (PID {proc.pid}) [force-killed]")

        except psutil.NoSuchProcess:
            killed.append(f"(already gone, PID {proc.pid})")
        except psutil.AccessDenied:
            failed.append(f"{proc.name()} (PID {proc.pid}) — access denied")
        except Exception as exc:
            failed.append(f"{proc.name()} (PID {proc.pid}) — {exc}")

    parts = []
    if killed:
        parts.append(f"Closed {len(killed)} process(es):\n" + "\n".join(f"  {k}" for k in killed))
    if skipped:
        parts.append("Skipped (protected):\n" + "\n".join(f"  {s}" for s in skipped))
    if failed:
        parts.append("Failed:\n" + "\n".join(f"  {f}" for f in failed))

    return "\n\n".join(parts) or "Nothing was closed."


def handle_vscode_open(data: dict) -> str:
    target = (
        data.get("app_path", "").strip()
        or data.get("folder", "").strip()
        or BASE_FOLDER
    )
    target = str(Path(target).expanduser())
    if not shutil.which("code"):
        return (
            "`code` command not found.\n"
            "Install VSCode and enable 'Add to PATH' during setup."
        )
    try:
        subprocess.Popen(["code", target])
        return f"Opened in VSCode: `{target}`"
    except Exception as exc:
        return f"Could not open VSCode: {exc}"
