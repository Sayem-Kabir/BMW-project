import axios from "axios";
import type {
  DriverAnalysis,
  MaintenanceHistoryResponse,
  MaintenanceLatestResponse,
  MaintenanceRunResponse,
  MaintenanceStatus,
  RoadAnalysis,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export async function getHealth() {
  const { data } = await api.get("/health");
  return data;
}

export async function getFleetOverview() {
  const { data } = await api.get("/api/v1/fleet/overview");
  return data;
}

/** Single-frame analysis via multipart upload (file / snapshot fallback). */
export async function analyzeDriverFrame(
  file: Blob,
  vehicleId = "test",
  sessionId = "test",
  filename = "frame.jpg"
): Promise<DriverAnalysis> {
  const form = new FormData();
  form.append("file", file, filename);
  const params = new URLSearchParams({
    vehicle_id: vehicleId,
    session_id: sessionId,
  });
  const res = await fetch(`${API_URL}/api/v1/driver/analysis?${params}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Analysis failed (${res.status})`);
  }
  return res.json() as Promise<DriverAnalysis>;
}

/** Module 2H single-frame road analysis with retained stream state. */
export async function analyzeRoadFrame(
  file: Blob,
  streamId = "road-ui",
  filename = "road-frame.jpg"
): Promise<RoadAnalysis> {
  const form = new FormData();
  form.append("file", file, filename);
  const params = new URLSearchParams({ stream_id: streamId });
  const res = await fetch(`${API_URL}/api/v1/road/analysis?${params}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail || `Road analysis failed (${res.status})`;
    throw new Error(String(detail));
  }
  return res.json() as Promise<RoadAnalysis>;
}

export async function resetRoadStream(streamId: string): Promise<boolean> {
  const res = await fetch(
    `${API_URL}/api/v1/road/streams/${encodeURIComponent(streamId)}`,
    { method: "DELETE" }
  );
  if (!res.ok) {
    throw new Error(`Could not reset road stream (${res.status})`);
  }
  const payload = (await res.json()) as { reset?: boolean };
  return Boolean(payload.reset);
}

export async function getRoadStatus(): Promise<RoadAnalysis> {
  const res = await fetch(`${API_URL}/api/v1/road/status`);
  if (!res.ok) {
    throw new Error(`Could not load road status (${res.status})`);
  }
  return res.json() as Promise<RoadAnalysis>;
}

export async function getMaintenanceStatus(): Promise<MaintenanceStatus> {
  const { data } = await api.get<MaintenanceStatus>("/api/v1/maintenance/status");
  return data;
}

export async function getMaintenanceLatest(
  vehicleId: string
): Promise<MaintenanceLatestResponse> {
  const { data } = await api.get<MaintenanceLatestResponse>(
    `/api/v1/maintenance/${encodeURIComponent(vehicleId)}`
  );
  return data;
}

export async function getMaintenanceHistory(
  vehicleId: string,
  limit = 100
): Promise<MaintenanceHistoryResponse> {
  const { data } = await api.get<MaintenanceHistoryResponse>(
    `/api/v1/maintenance/${encodeURIComponent(vehicleId)}/history`,
    { params: { limit } }
  );
  return data;
}

export async function runMaintenancePrediction(
  vehicleId: string,
  telemetry: Record<string, unknown>
): Promise<MaintenanceRunResponse> {
  const { data } = await api.post<MaintenanceRunResponse>(
    `/api/v1/maintenance/${encodeURIComponent(vehicleId)}/predict`,
    { telemetry }
  );
  return data;
}
