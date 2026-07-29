"""Module 8C — download / register model weights into ml/models/.

Usage (repo root):
  python -m ml.models.download_registry
  python -m ml.models.download_registry --only yolov8n_base,yolov8m_base
  python -m ml.models.download_registry --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"
MODELS_DIR = Path(__file__).resolve().parent


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def status_report() -> list[dict[str, Any]]:
    reg = load_registry()
    rows: list[dict[str, Any]] = []
    for entry in reg["entries"]:
        path = MODELS_DIR / entry["filename"]
        row: dict[str, Any] = {
            "id": entry["id"],
            "filename": entry["filename"],
            "present": path.is_file(),
            "required": bool(entry.get("required")),
            "source": entry.get("source"),
        }
        if path.is_file():
            row["bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
            try:
                from ml.models.signed_ota import verify_signed_weights

                row["signature"] = verify_signed_weights(path, require_signature=False)
            except Exception as exc:  # noqa: BLE001
                row["signature"] = {"ok": False, "error": str(exc)}
        rows.append(row)
    return rows


def download_ultralytics(name: str, dest: Path) -> Path:
    from ultralytics import YOLO

    # YOLO(name) downloads into CWD; copy into ml/models/
    model = YOLO(name)
    # Ultralytics keeps weights on the model object / cwd
    candidates = [
        Path(name),
        Path.cwd() / name,
        Path(getattr(model, "ckpt_path", "") or ""),
    ]
    src = next((p for p in candidates if p and p.is_file()), None)
    if src is None:
        # Force a predict to materialize weights
        model.predict(source=None, imgsz=32, verbose=False)
        src = Path(name) if Path(name).is_file() else Path.cwd() / name
    if not src.is_file():
        raise FileNotFoundError(f"Could not locate downloaded weights for {name}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def sync_entries(only: set[str] | None = None) -> list[dict[str, Any]]:
    reg = load_registry()
    results: list[dict[str, Any]] = []
    for entry in reg["entries"]:
        if only and entry["id"] not in only:
            continue
        dest = MODELS_DIR / entry["filename"]
        if dest.is_file():
            results.append({"id": entry["id"], "status": "exists", "path": str(dest)})
            continue
        if entry.get("source") == "ultralytics":
            path = download_ultralytics(entry["ultralytics_name"], dest)
            results.append({"id": entry["id"], "status": "downloaded", "path": str(path)})
        else:
            results.append(
                {
                    "id": entry["id"],
                    "status": "skipped_manual",
                    "hint": entry.get("train")
                    or "Place file manually or run Module 8D export",
                    "path": str(dest),
                }
            )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Module 8C model weight registry")
    parser.add_argument("--check", action="store_true", help="Print presence/checksums only")
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Comma-separated registry ids to download",
    )
    args = parser.parse_args(argv)

    if args.check:
        for row in status_report():
            mark = "OK" if row["present"] else "MISSING"
            print(f"[{mark}] {row['id']}: {row['filename']}")
            if row.get("sha256"):
                print(f"         sha256={row['sha256'][:16]}… size={row['bytes']}")
        return 0

    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    for row in sync_entries(only):
        print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
