import axios from "axios";
import type { DriverAnalysis } from "@/lib/types";

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
