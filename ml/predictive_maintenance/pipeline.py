"""Module 3G — unified 3B–3E predictive-maintenance orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Mapping

from ml.predictive_maintenance.battery_model import BatterySoHPredictor
from ml.predictive_maintenance.brake_model import BrakeConditionClassifier
from ml.predictive_maintenance.config import (
    BATTERY_SOH_FEATURES,
    ENGINE_ANOMALY_CRITICAL,
    ENGINE_ANOMALY_WARN,
    LOGISTICS_BRAKE_FEATURES,
    LOGISTICS_TIRE_MODEL_FEATURES,
    NEV_FAULT_FEATURES,
)
from ml.predictive_maintenance.engine_model import EngineFaultClassifier
from ml.predictive_maintenance.tire_model import TireWearPredictor
from ml.xai import TreeShapExplainer

COMPONENTS = ("engine", "brake", "battery", "tire")
COMPONENT_FEATURES: dict[str, tuple[str, ...]] = {
    "engine": tuple(NEV_FAULT_FEATURES),
    "brake": tuple(LOGISTICS_BRAKE_FEATURES),
    "battery": tuple(BATTERY_SOH_FEATURES),
    "tire": tuple(LOGISTICS_TIRE_MODEL_FEATURES),
}
_SEVERITY_RANK = {"normal": 0, "warning": 1, "critical": 2}


@dataclass(frozen=True)
class MaintenanceAlert:
    component: str
    severity: str
    message: str


@dataclass(frozen=True)
class ComponentPrediction:
    component: str
    status: str
    severity: str | None = None
    health_score: float | None = None
    maintenance_required: bool | None = None
    confidence: float | None = None
    result: dict[str, Any] | None = None
    explanation: dict[str, Any] | None = None
    explanation_error: str | None = None
    missing_features: tuple[str, ...] = ()
    error: str | None = None
    latency_ms: float = 0.0


@dataclass(frozen=True)
class MaintenancePipelineResult:
    status: str
    overall_severity: str
    timestamp: datetime
    components: dict[str, ComponentPrediction]
    alerts: tuple[MaintenanceAlert, ...]
    warnings: tuple[str, ...]
    processing_ms: float = 0.0
    stage_times_ms: dict[str, float] | None = None

    @property
    def succeeded(self) -> int:
        return sum(item.status == "ok" for item in self.components.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "overall_severity": self.overall_severity,
            "timestamp": self.timestamp.isoformat(),
            "components": {
                name: asdict(prediction)
                for name, prediction in self.components.items()
            },
            "alerts": [asdict(alert) for alert in self.alerts],
            "warnings": list(self.warnings),
            "processing_ms": self.processing_ms,
            "stage_times_ms": dict(self.stage_times_ms or {}),
        }


class MaintenancePipeline:
    """Run independent component models while preserving successful results."""

    def __init__(
        self,
        *,
        predictors: Mapping[str, Any] | None = None,
        explainer: TreeShapExplainer | None = None,
        enable_explanations: bool = True,
    ) -> None:
        defaults: dict[str, Any] = {
            "engine": EngineFaultClassifier(),
            "brake": BrakeConditionClassifier(),
            "battery": BatterySoHPredictor(),
            "tire": TireWearPredictor(),
        }
        if predictors:
            unknown = sorted(set(predictors) - set(COMPONENTS))
            if unknown:
                raise ValueError(f"Unknown maintenance components: {unknown}")
            defaults.update(predictors)
        self.predictors = defaults
        self.explainer = explainer or TreeShapExplainer(top_k=3)
        self.enable_explanations = enable_explanations

    @staticmethod
    def _component_input(
        telemetry: Mapping[str, Any],
        component: str,
    ) -> Mapping[str, Any]:
        nested = telemetry.get(component)
        return nested if isinstance(nested, Mapping) else telemetry

    @staticmethod
    def _result_dict(result: Any) -> dict[str, Any]:
        if is_dataclass(result) and not isinstance(result, type):
            return asdict(result)
        if isinstance(result, Mapping):
            return dict(result)
        raise TypeError("Predictor result must be a dataclass or mapping")

    @staticmethod
    def _health_score(component: str, result: Mapping[str, Any]) -> float:
        if component == "engine":
            probabilities = result.get("probabilities") or {}
            fault_mass = sum(
                float(value)
                for name, value in probabilities.items()
                if name != "normal"
            )
            return float(max(0.0, min(1.0, 1.0 - fault_mass)))
        if component == "brake":
            return {"Good": 1.0, "Fair": 0.5, "Poor": 0.15}.get(
                str(result.get("condition")),
                0.0,
            )
        if component == "battery":
            return float(max(0.0, min(1.0, float(result["soh_pct"]) / 100.0)))
        return float(max(0.0, min(1.0, 1.0 - float(result["wear_pct"]) / 100.0)))

    @staticmethod
    def _semantics(
        component: str,
        result: Mapping[str, Any],
    ) -> tuple[str, bool, float | None, int, int]:
        if component == "engine":
            fault = bool(result["fault_detected"])
            confidence = float(result["confidence"])
            if not fault:
                severity = "normal"
            elif confidence >= ENGINE_ANOMALY_CRITICAL:
                severity = "critical"
            elif confidence >= ENGINE_ANOMALY_WARN:
                severity = "warning"
            else:
                severity = "warning"
            class_id = int(result["class_id"])
            return severity, fault, confidence, class_id, -1 if class_id == 0 else 1
        if component == "brake":
            class_id = int(result["class_id"])
            return (
                str(result["severity"]),
                bool(result["maintenance_required"]),
                float(result["confidence"]),
                class_id,
                -1 if class_id == 0 else 1,
            )
        if component == "battery":
            return (
                str(result["severity"]),
                bool(result["maintenance_required"]),
                None,
                0,
                -1,
            )
        return (
            str(result["severity"]),
            bool(result["maintenance_required"]),
            None,
            0,
            1,
        )

    @staticmethod
    def _alert_message(component: str, result: Mapping[str, Any]) -> str:
        if component == "engine":
            return f"Engine fault classification: {result['class_name']}"
        if component == "brake":
            return f"Brake condition: {result['condition']}"
        if component == "battery":
            return f"Battery State-of-Health: {float(result['soh_pct']):.1f}%"
        return f"Tire wear proxy: {float(result['wear_pct']):.1f}%"

    @staticmethod
    def _overall_severity(components: Mapping[str, ComponentPrediction]) -> str:
        ranks = [
            _SEVERITY_RANK[item.severity]
            for item in components.values()
            if item.status == "ok" and item.severity in _SEVERITY_RANK
        ]
        if not ranks:
            return "unknown"
        for name, rank in (("critical", 2), ("warning", 1), ("normal", 0)):
            if max(ranks) == rank:
                return name
        return "unknown"

    def predict(
        self,
        telemetry: Mapping[str, Any],
        *,
        timestamp: datetime | None = None,
    ) -> MaintenancePipelineResult:
        started = perf_counter()
        components: dict[str, ComponentPrediction] = {}
        alerts: list[MaintenanceAlert] = []
        warnings: list[str] = []
        stage_times_ms: dict[str, float] = {}

        for component in COMPONENTS:
            stage_started = perf_counter()
            predictor = self.predictors[component]
            component_input = self._component_input(telemetry, component)
            features = COMPONENT_FEATURES[component]
            missing = tuple(
                feature for feature in features if feature not in component_input
            )
            if missing:
                message = f"{component}: missing {len(missing)} required features"
                warnings.append(message)
                components[component] = ComponentPrediction(
                    component=component,
                    status="unavailable",
                    missing_features=missing,
                    error=message,
                    latency_ms=(perf_counter() - stage_started) * 1000.0,
                )
                stage_times_ms[component] = components[component].latency_ms
                continue
            if hasattr(predictor, "ready") and not predictor.ready:
                message = f"{component}: model artifact unavailable"
                warnings.append(message)
                components[component] = ComponentPrediction(
                    component=component,
                    status="unavailable",
                    error=message,
                    latency_ms=(perf_counter() - stage_started) * 1000.0,
                )
                stage_times_ms[component] = components[component].latency_ms
                continue

            try:
                raw_result = predictor.predict(component_input)
                result = self._result_dict(raw_result)
                severity, required, confidence, output_index, risk_sign = (
                    self._semantics(component, result)
                )
                health_score = self._health_score(component, result)
            except Exception as exc:
                message = f"{component}: {type(exc).__name__}: {exc}"
                warnings.append(message)
                components[component] = ComponentPrediction(
                    component=component,
                    status="error",
                    error=message,
                    latency_ms=(perf_counter() - stage_started) * 1000.0,
                )
                stage_times_ms[component] = components[component].latency_ms
                continue

            explanation = None
            explanation_error = None
            if self.enable_explanations:
                try:
                    explanation = self.explainer.explain(
                        predictor.model,
                        component_input,
                        features,
                        output_index=output_index,
                        risk_sign=risk_sign,
                    ).to_dict()
                except Exception as exc:
                    explanation_error = f"{type(exc).__name__}: {exc}"
                    warnings.append(
                        f"{component}: explanation unavailable ({explanation_error})"
                    )

            if result.get("within_training_range") is False:
                warnings.append(f"{component}: input is outside the training range")
            latency_ms = (perf_counter() - stage_started) * 1000.0
            stage_times_ms[component] = latency_ms
            components[component] = ComponentPrediction(
                component=component,
                status="ok",
                severity=severity,
                health_score=health_score,
                maintenance_required=required,
                confidence=confidence,
                result=result,
                explanation=explanation,
                explanation_error=explanation_error,
                latency_ms=latency_ms,
            )
            if severity in ("warning", "critical"):
                alerts.append(
                    MaintenanceAlert(
                        component=component,
                        severity=severity,
                        message=self._alert_message(component, result),
                    )
                )

        succeeded = sum(item.status == "ok" for item in components.values())
        status = (
            "complete"
            if succeeded == len(COMPONENTS)
            else "partial"
            if succeeded
            else "failed"
        )
        return MaintenancePipelineResult(
            status=status,
            overall_severity=self._overall_severity(components),
            timestamp=timestamp or datetime.now(timezone.utc),
            components=components,
            alerts=tuple(alerts),
            warnings=tuple(warnings),
            processing_ms=(perf_counter() - started) * 1000.0,
            stage_times_ms=stage_times_ms,
        )
