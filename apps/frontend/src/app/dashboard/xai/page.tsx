"use client";

import { type FormEvent, useState } from "react";
import { RoleShell } from "@/components/dashboard/RoleShell";
import { explainXaiFrame, xaiHeatmapUrl } from "@/lib/api";
import type { XAIExplainResponse } from "@/lib/types";

const EVENT_TYPES = [
  { value: "drowsiness", label: "Drowsiness (eye focus)" },
  { value: "road_hazard", label: "Road hazard (lane focus)" },
  { value: "near_collision", label: "Near collision" },
];

type Attribution = "gradcam" | "ig" | "both";

export default function GradCamPage() {
  const [eventType, setEventType] = useState("drowsiness");
  const [attribution, setAttribution] = useState<Attribution>("both");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<XAIExplainResponse | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("frame") as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) {
      setError("Choose an image frame first.");
      return;
    }

    setError(null);
    setPending(true);
    setPreview(URL.createObjectURL(file));
    try {
      const payload = await explainXaiFrame(
        file,
        eventType,
        file.name,
        attribution
      );
      setResult(payload);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Vision XAI request failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <RoleShell subtitle="Grad-CAM / EigenCAM and Captum Integrated Gradients">
      <div className="grid gap-6 lg:grid-cols-2">
        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5"
        >
          <label className="mb-4 block text-sm">
            <span className="mb-1 block text-slate-400">Event type</span>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            >
              {EVENT_TYPES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label className="mb-4 block text-sm">
            <span className="mb-1 block text-slate-400">Attribution</span>
            <select
              value={attribution}
              onChange={(e) => setAttribution(e.target.value as Attribution)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            >
              <option value="gradcam">Grad-CAM only</option>
              <option value="ig">Integrated Gradients (8A)</option>
              <option value="both">Both</option>
            </select>
          </label>

          <label className="mb-4 block text-sm">
            <span className="mb-1 block text-slate-400">Frame image</span>
            <input
              name="frame"
              type="file"
              accept="image/*"
              className="w-full text-xs text-slate-300"
            />
          </label>

          {error ? (
            <p className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={pending}
            className="rounded-xl bg-fuchsia-600 px-4 py-2 text-sm font-semibold text-white hover:bg-fuchsia-500 disabled:opacity-50"
          >
            {pending ? "Generating…" : "Generate attribution"}
          </button>

          {preview ? (
            <div className="mt-5">
              <p className="mb-2 text-xs text-slate-500">Uploaded frame</p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={preview}
                alt="Uploaded frame"
                className="max-h-64 rounded-xl border border-slate-800"
              />
            </div>
          ) : null}
        </form>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="mb-3 text-sm font-semibold">Result</h2>
          {!result ? (
            <p className="text-sm text-slate-500">
              No heatmap yet. Upload a JPEG/PNG frame to run Grad-CAM / IG.
            </p>
          ) : (
            <div className="space-y-3 text-sm">
              <p className="whitespace-pre-wrap text-slate-200">
                {result.explanation}
              </p>
              <p className="text-xs text-slate-500">
                method={result.method} · phase={result.phase}
                {result.attribution ? ` · attribution=${result.attribution}` : ""}
                {result.activation_mass != null
                  ? ` · activation=${result.activation_mass.toFixed(3)}`
                  : ""}
              </p>
              {result.heatmap_url ? (
                <div>
                  <p className="mb-1 text-xs text-slate-500">Primary heatmap</p>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={xaiHeatmapUrl(result.heatmap_url)}
                    alt="Attribution heatmap"
                    className="max-h-80 rounded-xl border border-slate-700"
                  />
                </div>
              ) : null}
              {result.ig_heatmap_url &&
              result.ig_heatmap_url !== result.heatmap_url ? (
                <div>
                  <p className="mb-1 text-xs text-slate-500">
                    Integrated Gradients (8A)
                  </p>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={xaiHeatmapUrl(result.ig_heatmap_url)}
                    alt="IG heatmap"
                    className="max-h-80 rounded-xl border border-slate-700"
                  />
                </div>
              ) : null}
            </div>
          )}
        </section>
      </div>
    </RoleShell>
  );
}
