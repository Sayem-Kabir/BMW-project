"""
Download the Dlib 68-point facial landmark predictor (Module 1A).

Usage (from repo root):
    python -m ml.driver_monitoring.download_assets
    python -m ml.driver_monitoring.download_assets --force
"""

from __future__ import annotations

import bz2
import sys
import urllib.request
from pathlib import Path

from ml.driver_monitoring.config import (
    DLIB_LANDMARK_PATH,
    DLIB_LANDMARK_URL,
    DLIB_LANDMARK_URL_FALLBACK,
    ensure_models_dir,
    dlib_landmark_ready,
)


def _download(url: str, dest: Path) -> None:
    print(f"[download] {url}")
    print(f"           -> {dest}")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "bmw-ai-platform/1.0 (phase1a-asset-fetch)"},
    )

    def _progress(block_num: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            downloaded = block_num * block_size
            print(f"\r           {downloaded / 1e6:.1f} MB", end="", flush=True)
            return
        downloaded = min(total_size, block_num * block_size)
        pct = downloaded * 100 // total_size
        print(f"\r           {pct:3d}% ({downloaded / 1e6:.1f} MB)", end="", flush=True)

    # urlretrieve does not accept Request; use urlopen + manual write for headers
    with urllib.request.urlopen(request, timeout=120) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        chunk = 1024 * 256
        read = 0
        while True:
            data = resp.read(chunk)
            if not data:
                break
            out.write(data)
            read += len(data)
            if total:
                pct = read * 100 // total
                print(f"\r           {pct:3d}% ({read / 1e6:.1f} MB)", end="", flush=True)
            else:
                print(f"\r           {read / 1e6:.1f} MB", end="", flush=True)
    print()
    if dest.stat().st_size == 0:
        raise RuntimeError(f"Downloaded empty file from {url}")


def download_dlib_landmarks(force: bool = False) -> Path:
    ensure_models_dir()

    if dlib_landmark_ready() and not force:
        print(f"[ok] Already present: {DLIB_LANDMARK_PATH}")
        print(f"     size={DLIB_LANDMARK_PATH.stat().st_size / 1e6:.1f} MB")
        return DLIB_LANDMARK_PATH

    archive_path = DLIB_LANDMARK_PATH.with_suffix(".dat.bz2")
    last_error: Exception | None = None

    for url in (DLIB_LANDMARK_URL, DLIB_LANDMARK_URL_FALLBACK):
        try:
            _download(url, archive_path)
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[warn] Failed: {exc}")
            archive_path.unlink(missing_ok=True)

    if last_error is not None:
        print(
            "Manual fallback:\n"
            f"  1. Download {DLIB_LANDMARK_URL}\n"
            "  2. Extract the .bz2 (7-Zip or bunzip2)\n"
            f"  3. Place shape_predictor_68_face_landmarks.dat at:\n"
            f"     {DLIB_LANDMARK_PATH}",
            file=sys.stderr,
        )
        raise SystemExit(1) from last_error

    print(f"[extract] {archive_path} -> {DLIB_LANDMARK_PATH}")
    with bz2.open(archive_path, "rb") as src, open(DLIB_LANDMARK_PATH, "wb") as dst:
        dst.write(src.read())

    try:
        archive_path.unlink(missing_ok=True)
    except OSError as exc:
        print(f"[warn] Could not delete archive (safe to ignore): {exc}")
    size_mb = DLIB_LANDMARK_PATH.stat().st_size / 1e6
    print(f"[ok] Saved {DLIB_LANDMARK_PATH} ({size_mb:.1f} MB)")
    return DLIB_LANDMARK_PATH


def main() -> None:
    force = "--force" in sys.argv
    download_dlib_landmarks(force=force)
    if not dlib_landmark_ready():
        raise SystemExit("[error] Landmark file missing after download")
    print("[done] Module 1A asset ready.")


if __name__ == "__main__":
    main()
