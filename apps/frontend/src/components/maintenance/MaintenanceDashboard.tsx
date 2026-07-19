"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getMaintenanceHistory,
  getMaintenanceLatest,
  getMaintenanceStatus,
  runMaintenancePrediction,
} from "@/lib/api";
import type {
  MaintenanceComponent,
  MaintenanceComponentSummary,
  MaintenanceExplanation,
  MaintenancePrediction,
  MaintenanceRunResponse,
  MaintenanceSeverity,
} from "@/lib/types";

const DEFAULT_VEHICLE_ID = "00000000-0000-4000-8000-000000000003";
const COMPONENTS: MaintenanceComponent[] = [
  "engine",
  "brake",
  "battery",
  "tire",
];
const COMPONENT_LABELS: Record<MaintenanceComponent, string> = {
  engine: "Engine",
  brake: "Brakes",
  battery: "EV Battery",
  tire: "Tires",
};
const COMPONENT_COLORS: Record<MaintenanceComponent, string> = {
  engine: "#60a5fa",
  brake: "#f59e0b",
  battery: "#34d399",
  tire: "#a78bfa",
};
const SEVERITY_CLASSES: Record<MaintenanceSeverity, string> = {
  normal: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  warning: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  critical: "border-red-500/40 bg-red-500/10 text-red-300",
  unknown: "border-slate-600 bg-slate-800 text-slate-300",
};
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function errorMessage(error: unknown): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const data = error.response.data as { detail?: unknown };
    if (data.detail) return String(data.detail);
  }
  return error instanceof Error ? error.message : "Request failed";
}

function SeverityBadge({ severity }: { severity: MaintenanceSeverity }) {
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${SEVERITY_CLASSES[severity]}`}
    >
      {severity}
    </span>
  );
}

function HealthBar({ score }: { score: number | null }) {
  const percent = score === null ? 0 : Math.round(score * 100);
  const color =
    percent >= 70
      ? "bg-emerald-500"
      : percent >= 40
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <div>
      <div className="mb-2 flex items-end justify-between">
        <span className="text-xs uppercase tracking-wider text-slate-500">
          Health
        </span>
        <span className="text-3xl font-bold tabular-nums">
          {score === null ? "—" : `${percent}%`}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function ExplanationView({
  explanation,
}: {
  explanation: MaintenanceExplanation | null;
}) {
  if (!explanation?.top_features?.length) {
    return <p className="text-sm text-slate-500">No contribution data yet.</p>;
  }
  const max = Math.max(
    ...explanation.top_features.map((item) => Math.abs(item.contribution)),
    0.0001
  );
  return (
    <div className="space-y-3">
      {explanation.top_features.map((item) => {
        const increases = item.direction === "increases_risk";
        return (
          <div key={item.feature}>
            <div className="mb-1 flex justify-between gap-3 text-xs">
              <span className="truncate text-slate-300" title={item.feature}>
                {item.feature}
              </span>
              <span
                className={`shrink-0 tabular-nums ${
                  increases ? "text-red-300" : "text-emerald-300"
                }`}
              >
                {item.contribution >= 0 ? "+" : ""}
                {item.contribution.toFixed(3)}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full ${
                  increases ? "bg-red-500" : "bg-emerald-500"
                }`}
                style={{
                  width: `${(Math.abs(item.contribution) / max) * 100}%`,
                }}
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-600">
              input {item.value.toFixed(3)} ·{" "}
              {increases ? "increases risk" : "decreases risk"}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function summaryFromStored(
  component: MaintenanceComponent,
  prediction?: MaintenancePrediction
): MaintenanceComponentSummary {
  const stored = prediction?.shap_explanation;
  return {
    component,
    status: prediction ? "ok" : "unavailable",
    severity: stored?.severity ?? null,
    health_score: prediction?.health_score ?? null,
    maintenance_required: stored?.maintenance_required ?? null,
    confidence: prediction?.confidence ?? null,
    result: stored?.result ?? null,
    explanation: stored?.explanation ?? null,
    explanation_error: stored?.explanation_error ?? null,
    missing_features: [],
    error: prediction ? null : "No persisted prediction",
    latency_ms: 0,
  };
}

function ComponentCard({ data }: { data: MaintenanceComponentSummary }) {
  const severity = data.severity ?? "unknown";
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
            {data.status}
          </p>
          <h3 className="text-lg font-semibold">
            {COMPONENT_LABELS[data.component]}
          </h3>
        </div>
        <SeverityBadge severity={severity} />
      </div>
      <HealthBar score={data.health_score} />
      <div className="my-5 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg bg-slate-950/70 p-3">
          <p className="text-xs text-slate-500">Confidence</p>
          <p className="mt-1 font-semibold tabular-nums">
            {data.confidence === null
              ? "—"
              : `${Math.round(data.confidence * 100)}%`}
          </p>
        </div>
        <div className="rounded-lg bg-slate-950/70 p-3">
          <p className="text-xs text-slate-500">Maintenance</p>
          <p
            className={`mt-1 font-semibold ${
              data.maintenance_required ? "text-red-300" : "text-emerald-300"
            }`}
          >
            {data.maintenance_required === null
              ? "Unknown"
              : data.maintenance_required
                ? "Required"
                : "Not required"}
          </p>
        </div>
      </div>
      {data.status !== "ok" && (
        <div className="mb-5 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
          <p>{data.error || "Component unavailable"}</p>
          {data.missing_features.length > 0 && (
            <p className="mt-2 text-slate-400">
              Missing: {data.missing_features.join(", ")}
            </p>
          )}
        </div>
      )}
      <div className="border-t border-slate-800 pt-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Top feature contributions
        </p>
        <ExplanationView explanation={data.explanation} />
      </div>
    </article>
  );
}

function buildHistoryData(history: MaintenancePrediction[]) {
  const rows = new Map<string, Record<string, string | number>>();
  [...history].reverse().forEach((item, index) => {
    const key = item.created_at ?? `sample-${index}`;
    const row = rows.get(key) ?? {
      label: item.created_at
        ? new Date(item.created_at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })
        : `#${index + 1}`,
    };
    row[item.component] = Math.round(item.health_score * 100);
    rows.set(key, row);
  });
  return Array.from(rows.values());
}

export function MaintenanceDashboard() {
  const queryClient = useQueryClient();
  const [vehicleId, setVehicleId] = useState(DEFAULT_VEHICLE_ID);
  const [telemetryText, setTelemetryText] = useState("{}");
  const [inputError, setInputError] = useState<string | null>(null);
  const validVehicle = UUID_PATTERN.test(vehicleId.trim());

  const statusQuery = useQuery({
    queryKey: ["maintenance-status"],
    queryFn: getMaintenanceStatus,
    refetchInterval: 60_000,
  });
  const latestQuery = useQuery({
    queryKey: ["maintenance-latest", vehicleId],
    queryFn: () => getMaintenanceLatest(vehicleId),
    enabled: validVehicle,
    refetchInterval: 30_000,
  });
  const historyQuery = useQuery({
    queryKey: ["maintenance-history", vehicleId],
    queryFn: () => getMaintenanceHistory(vehicleId, 100),
    enabled: validVehicle,
    refetchInterval: 30_000,
  });
  const prediction = useMutation({
    mutationFn: (telemetry: Record<string, unknown>) =>
      runMaintenancePrediction(vehicleId, telemetry),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["maintenance-latest", vehicleId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["maintenance-history", vehicleId],
      });
    },
  });

  const live = prediction.data;
  const latestByComponent = useMemo(
    () =>
      new Map(
        (latestQuery.data?.predictions ?? []).map((item) => [
          item.component,
          item,
        ])
      ),
    [latestQuery.data]
  );
  const componentData = useMemo(
    () =>
      COMPONENTS.map((component) =>
        live
          ? live.components[component]
          : summaryFromStored(component, latestByComponent.get(component))
      ),
    [live, latestByComponent]
  );
  const historyData = useMemo(
    () => buildHistoryData(historyQuery.data?.history ?? []),
    [historyQuery.data]
  );

  const loadTemplate = () => {
    if (!statusQuery.data) return;
    const template = Object.fromEntries(
      COMPONENTS.map((component) => [
        component,
        Object.fromEntries(
          statusQuery.data.components[component].required_features.map(
            (feature) => [feature, 0]
          )
        ),
      ])
    );
    setTelemetryText(JSON.stringify(template, null, 2));
    setInputError(null);
  };

  const runPrediction = () => {
    setInputError(null);
    if (!validVehicle) {
      setInputError("Vehicle ID must be a valid UUID.");
      return;
    }
    try {
      const parsed: unknown = JSON.parse(telemetryText);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Telemetry must be a JSON object.");
      }
      if (Object.keys(parsed as object).length === 0) {
        throw new Error("Telemetry must not be empty.");
      }
      prediction.mutate(parsed as Record<string, unknown>);
    } catch (error) {
      setInputError(errorMessage(error));
    }
  };

  const activeResult: MaintenanceRunResponse | undefined = live;
  const overallSeverity = activeResult?.overall_severity ?? "unknown";
  const alerts = activeResult?.alerts ?? [];
  const requestError =
    prediction.error || statusQuery.error || latestQuery.error || historyQuery.error;

  return (
    <div className="space-y-7">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <label className="block">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
              Vehicle UUID
            </span>
            <input
              value={vehicleId}
              onChange={(event) => setVehicleId(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 font-mono text-sm text-white outline-none focus:border-blue-500"
              aria-invalid={!validVehicle}
            />
          </label>
          <div className="flex flex-wrap gap-3">
            <button
              className="secondary-button"
              onClick={() => {
                void latestQuery.refetch();
                void historyQuery.refetch();
              }}
              disabled={!validVehicle}
            >
              Refresh history
            </button>
            <button className="primary-button" onClick={loadTemplate}>
              Load feature template
            </button>
          </div>
        </div>
        {!validVehicle && (
          <p className="mt-2 text-sm text-red-300">Enter a valid vehicle UUID.</p>
        )}
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <Metric
            label="Model artifacts"
            value={
              statusQuery.isLoading
                ? "Checking"
                : statusQuery.data?.all_models_ready
                  ? "4 / 4 ready"
                  : "Setup incomplete"
            }
          />
          <Metric
            label="Latest pipeline"
            value={activeResult?.status ?? "Stored data"}
          />
          <Metric
            label="Overall severity"
            value={<SeverityBadge severity={overallSeverity} />}
          />
        </div>
      </section>

      {(requestError || inputError) && (
        <div
          role="alert"
          className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"
        >
          {inputError || errorMessage(requestError)}
        </div>
      )}

      {alerts.length > 0 && (
        <section aria-label="Maintenance alerts" className="space-y-3">
          {alerts.map((alert, index) => (
            <div
              key={`${alert.component}-${index}`}
              role="alert"
              className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${SEVERITY_CLASSES[alert.severity]}`}
            >
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider">
                  {COMPONENT_LABELS[alert.component]} alert
                </p>
                <p className="mt-1 font-medium">{alert.message}</p>
              </div>
              <SeverityBadge severity={alert.severity} />
            </div>
          ))}
        </section>
      )}

      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-blue-300">
              Component health
            </p>
            <h2 className="text-2xl font-bold">Vehicle condition</h2>
          </div>
          {activeResult && (
            <p className="text-sm text-slate-400">
              {activeResult.persisted} rows persisted ·{" "}
              {activeResult.processing_ms.toFixed(1)} ms
            </p>
          )}
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {componentData.map((component) => (
            <ComponentCard key={component.component} data={component} />
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-5">
            <p className="text-xs uppercase tracking-[0.2em] text-blue-300">
              Persisted history
            </p>
            <h2 className="text-xl font-bold">Health trend</h2>
          </div>
          {historyData.length === 0 ? (
            <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-slate-700 text-sm text-slate-500">
              No persisted predictions for this vehicle yet.
            </div>
          ) : (
            <div className="h-72" aria-label="Component health history chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="label" stroke="#64748b" fontSize={11} />
                  <YAxis
                    domain={[0, 100]}
                    stroke="#64748b"
                    fontSize={11}
                    unit="%"
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#020617",
                      border: "1px solid #334155",
                      borderRadius: 8,
                    }}
                  />
                  <Legend />
                  {COMPONENTS.map((component) => (
                    <Line
                      key={component}
                      type="monotone"
                      dataKey={component}
                      name={COMPONENT_LABELS[component]}
                      stroke={COMPONENT_COLORS[component]}
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <p className="text-xs uppercase tracking-[0.2em] text-blue-300">
              Live inference
            </p>
            <h2 className="text-xl font-bold">Telemetry payload</h2>
            <p className="mt-2 text-sm text-slate-400">
              Use nested engine, brake, battery, and tire feature objects. Load
              the contract template, then replace placeholders with real values.
            </p>
          </div>
          <textarea
            value={telemetryText}
            onChange={(event) => setTelemetryText(event.target.value)}
            spellCheck={false}
            className="h-72 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 p-3 font-mono text-xs leading-5 text-slate-200 outline-none focus:border-blue-500"
            aria-label="Maintenance telemetry JSON"
          />
          <button
            className="primary-button mt-4 w-full"
            onClick={runPrediction}
            disabled={prediction.isPending || !validVehicle}
          >
            {prediction.isPending ? "Running 3G pipeline…" : "Run prediction"}
          </button>
          <p className="mt-3 text-xs text-slate-500">
            Missing component features remain explicit; the UI never fabricates
            telemetry.
          </p>
        </div>
      </section>

      {activeResult?.warnings.length ? (
        <details className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <summary className="cursor-pointer text-sm font-semibold text-amber-200">
            Pipeline warnings ({activeResult.warnings.length})
          </summary>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-400">
            {activeResult.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
      <div className="mt-2 text-lg font-semibold capitalize">{value}</div>
    </div>
  );
}
