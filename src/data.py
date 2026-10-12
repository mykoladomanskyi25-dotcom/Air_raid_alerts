"""Download the alert dataset at a pinned commit and load it."""
from __future__ import annotations

import hashlib
import json
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config

USER_AGENT = "air-raid-forecast/0.1 (KSE Agentic AI School, Stage 2)"


def _get(url: str, timeout: int = 300) -> bytes:
    """HTTPS GET with the standard library.

    Certificates are verified against the operating system's store. `requests` ships its own
    CA bundle (certifi), which failed on this machine with CERTIFICATE_VERIFY_FAILED.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
        return resp.read()


def raw_url(file: str, commit: str) -> str:
    return f"https://raw.githubusercontent.com/{config.DATASET_REPO}/{commit}/{file}"


def latest_commit() -> tuple[str, str]:
    """(sha, committer date UTC) of the newest commit on the dataset's main branch."""
    url = f"https://api.github.com/repos/{config.DATASET_REPO}/commits/main"
    data = json.loads(_get(url, timeout=30))
    return data["sha"], data["commit"]["committer"]["date"]


def resolve_commit(latest: bool) -> tuple[str, str]:
    if latest:
        return latest_commit()
    return config.DATASET_COMMIT, config.DATASET_COMMIT_TIME_UTC


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(file: str, commit: str) -> Path:
    """Fetch one dataset file into data/raw/<commit>/ unless it is already cached."""
    dest = config.RAW_DIR / commit / Path(file).name
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = raw_url(file, commit)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(_get(url))
    tmp.replace(dest)
    meta = {"url": url, "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    dest.with_name(dest.name + ".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return dest


def write_snapshot(commit: str, commit_time: str, files: dict[str, Path]) -> dict:
    """Record exactly which input the run used (reports/data_snapshot.json)."""
    described = {}
    for name, path in files.items():
        meta_path = path.with_name(path.name + ".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        described[name] = {**meta, "bytes": path.stat().st_size, "sha256": _sha256(path)}
    snap = {"repo": config.DATASET_REPO, "commit": commit, "commit_time_utc": commit_time, "files": described}
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.REPORTS_DIR / "data_snapshot.json"
    out.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return snap


def load_raw(path: Path) -> pd.DataFrame:
    """Read a dataset file with every column as text, exactly as published."""
    return pd.read_csv(path, dtype=str)
