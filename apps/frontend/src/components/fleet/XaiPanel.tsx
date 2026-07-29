"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { MediaThumb } from "@/components/MediaThumb";
import { explainXai, xaiHeatmapUrl } from "@/lib/api";
import type { XAIExplainResponse } from "@/lib/types";

interface Props {
  eventId?: string;
  eventType?: string;
  component?: string;
  vehicleId?: string;
  className?: string;
  autoLabel?: string;
}

type ShapPayload = {
  component?: string;
  health_score?: number;
  top_features?: Array<{
    feature?: string;
    name?: string;
    contribution?: number;
    impact?: number;
    direction?: string;
  }>;
  waterfall_ascii?: string;
  shap_plot_base64?: string;
};

export function XaiPanel({
  eventId,
  eventType,
  component,
  vehicleId,
  className = "",
  autoLabel = "Explain",
}: Props) {
  const [result, setResult] = useState<XAIExplainResponse | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      explainXai({
        event_id: eventId,
        event_type: eventType,
        component,
        vehicle_id: vehicleId,
      }),
    onSuccess: setResult,
  });

  const shap = result?.shap_values as ShapPayload | undefined;
  const ruleTrace = result?.rule_trace as
    | {
        event_type?: string;
        severity?: string;
        telemetry_snapshot?: Record<string, unknown>;
      }
    | null
    | undefined;

  const canExplain = Boolean(eventId || eventType || (vehicleId && component));

  return (
    <div
      className={`rounded-xl border border-violet-500/20 bg-slate-950/80 p-3 ${className}`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-300">
            XAI panel · 6G
          </h3>
          {(component || eventType || eventId) && (
            <p className="mt-0.5 text-[10px] text-slate-500">
              {[
                component ? `component=${component}` : null,
                eventType ? `type=${eventType}` : null,
                eventId ? `event=${eventId.slice(0, 8)}…` : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </div>
        <button
          type="button"
          disabled={mutation.isPending || !canExplain}
          onClick={() => mutation.mutate()}
          className="rounded-lg border border-violet-500/40 px-2.5 py-1 text-[11px] text-violet-100 hover:bg-violet-500/10 disabled:opacity-50"
        >
          {mutation.isPending ? "Explaining…" : autoLabel}
        </button>
      </div>

      {mutation.isError ? (
        <p className="text-xs text-red-300">Could not load explanation.</p>
      ) : null}

      {result ? (
        <div className="space-y-3 text-xs text-slate-300">
          <p className="whitespace-pre-wrap leading-relaxed">{result.explanation}</p>
          <p className="text-[10px] text-slate-500">
            method={result.method} · phase={result.phase}
            {result.activation_mass != null
              ? ` · activation=${Number(result.activation_mass).toFixed(3)}`
              : ""}
          </p>

          {ruleTrace ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-2">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Rule trace
              </p>
              <p className="text-[11px] text-slate-300">
                {ruleTrace.event_type || "event"} · severity=
                {ruleTrace.severity || "—"}
              </p>
              {ruleTrace.telemetry_snapshot ? (
                <pre className="mt-1 max-h-28 overflow-auto text-[10px] text-slate-500">
                  {JSON.stringify(ruleTrace.telemetry_snapshot, null, 2)}
                </pre>
              ) : null}
            </div>
          ) : null}

          {result.heatmap_url ? (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Vision attribution
              </p>
              <MediaThumb
                src={xaiHeatmapUrl(result.heatmap_url)}
                alt="Attribution heatmap"
                className="max-h-48 rounded-lg border border-slate-800 object-contain"
                width={480}
                height={270}
              />
            </div>
          ) : null}

          {result.ig_heatmap_url &&
          result.ig_heatmap_url !== result.heatmap_url ? (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Integrated Gradients (8A)
              </p>
              <MediaThumb
                src={xaiHeatmapUrl(result.ig_heatmap_url)}
                alt="IG heatmap"
                className="max-h-48 rounded-lg border border-slate-800 object-contain"
                width={480}
                height={270}
              />
            </div>
          ) : null}

          {shap?.shap_plot_base64 ? (
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                SHAP contributions
                {shap.component ? ` · ${shap.component}` : ""}
                {shap.health_score != null
                  ? ` · health ${(Number(shap.health_score) * 100).toFixed(0)}%`
                  : ""}
              </p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/png;base64,${shap.shap_plot_base64}`}
                alt="SHAP contributions"
                className="max-h-48 w-full rounded-lg border border-slate-800 bg-white"
              />
            </div>
          ) : null}

          {shap?.top_features?.length ? (
            <ul className="space-y-1 rounded-lg border border-slate-800 bg-slate-900/60 p-2">
              {shap.top_features.slice(0, 5).map((feat, idx) => {
                const name = String(feat.feature || feat.name || `f${idx}`);
                const value = Number(feat.contribution ?? feat.impact ?? 0);
                return (
                  <li
                    key={`${name}-${idx}`}
                    className="flex items-center justify-between gap-2 text-[11px]"
                  >
                    <span className="truncate text-slate-300">{name}</span>
                    <span
                      className={
                        value >= 0 ? "text-red-300" : "text-emerald-300"
                      }
                    >
                      {value >= 0 ? "+" : ""}
                      {value.toFixed(4)}
                      {feat.direction ? ` · ${feat.direction}` : ""}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : null}

          {shap?.waterfall_ascii ? (
            <pre className="overflow-x-auto rounded-lg bg-slate-900 p-2 text-[10px] text-slate-400">
              {shap.waterfall_ascii}
            </pre>
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-slate-500">
          {canExplain
            ? "Generate NL explanation with rule trace / SHAP / Grad-CAM."
            : "Select an event or maintenance component to explain."}
        </p>
      )}
    </div>
  );
}
