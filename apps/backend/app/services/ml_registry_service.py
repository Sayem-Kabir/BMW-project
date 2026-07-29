"""Model registry + MLflow promote — Spec Phase 11A."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Local fallback stages when MLflow is down / unconfigured
_LOCAL_STAGES: dict[str, dict[str, Any]] = {
    "driver_monitor": {"stage": "Staging", "version": "1", "run_id": None},
    "risk_engine": {"stage": "Production", "version": "2", "run_id": None},
    "maintenance_xgb": {"stage": "Staging", "version": "1", "run_id": None},
}

# Production promote requires eval >= this unless caller raises the bar further
DEFAULT_MIN_EVAL_FOR_PRODUCTION = 0.80


def _mlflow_client():
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        return MlflowClient()
    except Exception as exc:  # noqa: BLE001
        logger.debug("MLflow client unavailable: %s", exc)
        return None


def list_registered_models() -> list[dict[str, Any]]:
    client = _mlflow_client()
    if client is not None:
        try:
            out: list[dict[str, Any]] = []
            for rm in client.search_registered_models():
                versions = client.search_model_versions(f"name='{rm.name}'")
                latest = sorted(versions, key=lambda v: int(v.version), reverse=True)
                stage = latest[0].current_stage if latest else "None"
                out.append(
                    {
                        "name": rm.name,
                        "stage": stage,
                        "versions": [
                            {
                                "version": v.version,
                                "stage": v.current_stage,
                                "run_id": v.run_id,
                            }
                            for v in latest[:10]
                        ],
                        "source": "mlflow",
                    }
                )
            if out:
                return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("MLflow list failed, using local registry: %s", exc)

    return [
        {
            "name": name,
            "stage": meta["stage"],
            "versions": [
                {
                    "version": meta["version"],
                    "stage": meta["stage"],
                    "run_id": meta.get("run_id"),
                }
            ],
            "source": "local",
        }
        for name, meta in sorted(_LOCAL_STAGES.items())
    ]


def list_versions(name: str) -> list[dict[str, Any]]:
    client = _mlflow_client()
    if client is not None:
        try:
            versions = client.search_model_versions(f"name='{name}'")
            return [
                {
                    "version": v.version,
                    "stage": v.current_stage,
                    "run_id": v.run_id,
                    "status": v.status,
                }
                for v in sorted(versions, key=lambda x: int(x.version), reverse=True)
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("MLflow versions failed: %s", exc)
    meta = _LOCAL_STAGES.get(name)
    if not meta:
        return []
    return [
        {
            "version": meta["version"],
            "stage": meta["stage"],
            "run_id": meta.get("run_id"),
            "status": "READY",
        }
    ]


def evaluate_gate(
    *,
    target_stage: str,
    eval_metric_value: float,
    min_eval_metric: float | None,
) -> tuple[bool, float, str]:
    """Return (ok, required_min, reason). Production always requires a floor."""
    required = float(min_eval_metric) if min_eval_metric is not None else 0.0
    if target_stage.lower() == "production":
        required = max(required, DEFAULT_MIN_EVAL_FOR_PRODUCTION)
    if eval_metric_value < required:
        return (
            False,
            required,
            f"Eval metric {eval_metric_value:.4f} < required {required:.4f} — promotion blocked",
        )
    return True, required, "ok"


def promote(
    name: str,
    *,
    target_stage: str = "Production",
    version: str | None = None,
    eval_metric_value: float = 0.9,
    min_eval_metric: float | None = None,
) -> dict[str, Any]:
    ok, required, reason = evaluate_gate(
        target_stage=target_stage,
        eval_metric_value=eval_metric_value,
        min_eval_metric=min_eval_metric,
    )
    if not ok:
        raise ValueError(reason)

    stage_norm = target_stage.capitalize()
    if stage_norm.lower() == "production":
        stage_norm = "Production"
    elif stage_norm.lower() == "staging":
        stage_norm = "Staging"

    client = _mlflow_client()
    if client is not None:
        try:
            versions = client.search_model_versions(f"name='{name}'")
            if not versions and name not in _LOCAL_STAGES:
                raise ValueError(f"Unknown model {name!r}")
            if versions:
                chosen = None
                if version:
                    chosen = next((v for v in versions if v.version == str(version)), None)
                    if chosen is None:
                        raise ValueError(f"Version {version} not found for {name}")
                else:
                    chosen = sorted(versions, key=lambda v: int(v.version), reverse=True)[0]
                previous = chosen.current_stage
                client.transition_model_version_stage(
                    name=name,
                    version=chosen.version,
                    stage=stage_norm,
                    archive_existing_versions=(stage_norm == "Production"),
                )
                return {
                    "name": name,
                    "version": chosen.version,
                    "previous_stage": previous,
                    "stage": stage_norm,
                    "eval_metric_value": eval_metric_value,
                    "min_eval_metric": required,
                    "source": "mlflow",
                    "phase": "11A",
                }
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("MLflow promote failed, falling back to local: %s", exc)

    if name not in _LOCAL_STAGES:
        raise ValueError(f"Unknown model {name!r}")
    previous = _LOCAL_STAGES[name]["stage"]
    if version:
        _LOCAL_STAGES[name]["version"] = str(version)
    _LOCAL_STAGES[name]["stage"] = stage_norm
    return {
        "name": name,
        "version": _LOCAL_STAGES[name]["version"],
        "previous_stage": previous,
        "stage": stage_norm,
        "eval_metric_value": eval_metric_value,
        "min_eval_metric": required,
        "source": "local",
        "phase": "11A",
    }
