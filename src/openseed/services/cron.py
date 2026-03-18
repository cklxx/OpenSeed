"""Crontab management for scheduled watch runs.

Crontab entry lifecycle:
┌────────────┐     ┌──────────────┐     ┌────────────┐
│ schedule   │────▶│ install      │────▶│ cron fires │
│ (user)     │     │ crontab entry│     │ daily      │
└────────────┘     └──────────────┘     └─────┬──────┘
                                              │
                                        ┌─────▼──────┐
                                        │ openseed   │
                                        │ watch run  │
                                        │ >> log     │
                                        └────────────┘
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_MARKER = "# openseed-watch-cron"


def _openseed_bin() -> str:
    """Find the openseed binary path."""
    which = shutil.which("openseed")
    return which if which else "openseed"


def _log_path() -> Path:
    log = Path.home() / ".openseed" / "watch.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    return log


def _cron_line() -> str:
    """Build the crontab entry: daily at 8am, append to log."""
    cmd = _openseed_bin()
    log = _log_path()
    return f"0 8 * * * {cmd} watch run >> {log} 2>&1 {_MARKER}"


def _read_crontab() -> str:
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
        return result.stdout if result.returncode == 0 else ""
    except FileNotFoundError as exc:
        raise FileNotFoundError("crontab not found. On macOS you can use launchd instead.") from exc


def _write_crontab(content: str) -> None:
    subprocess.run(["crontab", "-"], input=content, text=True, check=True, capture_output=True)


def is_scheduled() -> bool:
    """Check if openseed watch cron is currently installed."""
    return _MARKER in _read_crontab()


def install() -> str:
    """Install the openseed watch cron entry. Returns the cron line."""
    current = _read_crontab()
    if _MARKER in current:
        return "already scheduled"
    new_line = _cron_line()
    updated = current.rstrip("\n") + "\n" + new_line + "\n" if current else new_line + "\n"
    _write_crontab(updated)
    return new_line


def uninstall() -> bool:
    """Remove the openseed watch cron entry. Returns True if removed."""
    current = _read_crontab()
    if _MARKER not in current:
        return False
    lines = [ln for ln in current.splitlines() if _MARKER not in ln]
    _write_crontab("\n".join(lines) + "\n" if lines else "")
    return True


def get_status() -> dict:
    """Return cron status: scheduled, log_path, last_lines."""
    log = _log_path()
    last_lines: list[str] = []
    if log.exists():
        all_lines = log.read_text().strip().splitlines()
        last_lines = all_lines[-20:]
    return {
        "scheduled": is_scheduled(),
        "log_path": str(log),
        "last_lines": last_lines,
    }
