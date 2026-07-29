"""Signed model weight verification — Spec Section 19.1 / UNECE R155-R156 style."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Demo HMAC key — override via env MODEL_SIGNING_SECRET in production
DEFAULT_SECRET = b"bmw-ai-dev-model-signing-key-change-me"


def signing_secret(override: str | None = None) -> bytes:
    if override:
        return override.encode("utf-8")
    try:
        from app.core.config import settings

        secret = getattr(settings, "weight_signing_secret", "") or ""
        if secret:
            return secret.encode("utf-8")
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_SECRET


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sign_digest(digest_hex: str, *, secret: bytes | None = None) -> str:
    key = secret or signing_secret()
    return hmac.new(key, digest_hex.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_file(path: Path, *, secret: bytes | None = None) -> dict[str, str]:
    digest = sha256_file(path)
    sig = sign_digest(digest, secret=secret)
    sig_path = path.with_suffix(path.suffix + ".sig")
    payload = {"sha256": digest, "signature": sig, "alg": "HMAC-SHA256"}
    sig_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def verify_signed_weights(
    path: Path | str,
    *,
    require_signature: bool = False,
    secret: bytes | None = None,
) -> dict[str, Any]:
    """Verify optional sidecar ``.sig`` before loading model weights."""
    p = Path(path)
    result: dict[str, Any] = {
        "path": str(p),
        "ok": True,
        "verified": False,
        "phase": "19.1",
    }
    if not p.is_file():
        result["ok"] = False
        result["error"] = "file_missing"
        if require_signature:
            raise FileNotFoundError(f"Model weights missing: {p}")
        return result

    sig_path = p.with_suffix(p.suffix + ".sig")
    if not sig_path.is_file():
        result["message"] = "no_signature_sidecar"
        if require_signature:
            result["ok"] = False
            raise PermissionError(f"Missing signature for {p}")
        logger.debug("No signature for %s — allowing unsigned load", p.name)
        return result

    meta = json.loads(sig_path.read_text(encoding="utf-8"))
    digest = sha256_file(p)
    expected = sign_digest(digest, secret=secret)
    if not hmac.compare_digest(expected, str(meta.get("signature", ""))):
        result["ok"] = False
        result["error"] = "signature_mismatch"
        raise PermissionError(f"Signature verification failed for {p}")
    if meta.get("sha256") and meta["sha256"] != digest:
        result["ok"] = False
        result["error"] = "sha256_mismatch"
        raise PermissionError(f"Checksum mismatch for {p}")
    result["verified"] = True
    result["sha256"] = digest
    return result
