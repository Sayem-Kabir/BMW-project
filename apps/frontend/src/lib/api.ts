import axios from "axios";
import type {
  AssistantSseDone,
  AssistantSseMeta,
  AssistantSseToken,
  ChatResponse,
  ConversationDetailResponse,
  ConversationListResponse,
  DriverAnalysis,
  EventDetectResponse,
  EventListResponse,
  MaintenanceHistoryResponse,
  MaintenanceLatestResponse,
  MaintenanceRunResponse,
  MaintenanceStatus,
  RiskComputeResponse,
  RiskHistoryResponse,
  RiskScore,
  RoadAnalysis,
  SafetyEvent,
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

const DEFAULT_ORG_ID = "00000000-0000-4000-8000-000000000010";

export function apiWebSocketUrl(path: string): string {
  const base = API_URL.replace(/^http/i, (match) =>
    match.toLowerCase() === "https" ? "wss" : "ws"
  );
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export function fleetRiskWebSocketUrl(orgId = DEFAULT_ORG_ID): string {
  return apiWebSocketUrl(`/api/v1/fleet/ws/${encodeURIComponent(orgId)}`);
}

/** Turn `minio://bucket/key` into a console browse link when possible. */
export function clipLink(url: string | null | undefined): {
  href: string | null;
  label: string;
} {
  if (!url) {
    return { href: null, label: "No clip stored" };
  }
  if (url.startsWith("minio://")) {
    const rest = url.slice("minio://".length);
    const slash = rest.indexOf("/");
    if (slash > 0) {
      const bucket = rest.slice(0, slash);
      const object = rest.slice(slash + 1);
      const consoleBase =
        process.env.NEXT_PUBLIC_MINIO_CONSOLE_URL || "http://localhost:9001";
      return {
        href: `${consoleBase}/browser/${bucket}/${object}`,
        label: url,
      };
    }
  }
  return { href: url, label: url };
}

export async function getCurrentRisk(vehicleId: string): Promise<RiskScore> {
  const { data } = await api.get<RiskScore>(
    `/api/v1/risk/current/${encodeURIComponent(vehicleId)}`
  );
  return data;
}

export async function computeRisk(
  vehicleId: string,
  body: {
    driver_state?: Record<string, unknown>;
    road_state?: Record<string, unknown>;
    telemetry?: Record<string, unknown>;
    publish?: boolean;
    cache?: boolean;
    persist?: boolean;
  }
): Promise<RiskComputeResponse> {
  const { data } = await api.post<RiskComputeResponse>(
    `/api/v1/risk/${encodeURIComponent(vehicleId)}/compute`,
    body
  );
  return data;
}

export async function getRiskHistory(
  vehicleId: string,
  limit = 50
): Promise<RiskHistoryResponse> {
  const { data } = await api.get<RiskHistoryResponse>(
    `/api/v1/risk/history/${encodeURIComponent(vehicleId)}`,
    { params: { limit } }
  );
  return data;
}

export async function getSafetyEvents(
  vehicleId: string,
  params?: { limit?: number; severity?: string; acknowledged?: boolean }
): Promise<EventListResponse> {
  const { data } = await api.get<EventListResponse>(
    `/api/v1/events/${encodeURIComponent(vehicleId)}`,
    { params }
  );
  return data;
}

export async function acknowledgeSafetyEvent(
  eventId: string,
  driverId?: string
): Promise<SafetyEvent> {
  const { data } = await api.post<SafetyEvent>(
    `/api/v1/events/detail/${encodeURIComponent(eventId)}/acknowledge`,
    driverId ? { driver_id: driverId } : {}
  );
  return data;
}

export async function detectSafetyEvents(
  vehicleId: string,
  body: {
    driver_id: string;
    session_id?: string;
    driver_state?: Record<string, unknown>;
    road_state?: Record<string, unknown>;
    telemetry?: Record<string, unknown>;
    risk_score?: number;
    attach_clips?: boolean;
    enqueue_clip_retry?: boolean;
  }
): Promise<EventDetectResponse> {
  const { data } = await api.post<EventDetectResponse>(
    `/api/v1/events/${encodeURIComponent(vehicleId)}/detect`,
    body
  );
  return data;
}

export async function chatAssistant(body: {
  message: string;
  vehicle_id?: string;
  driver_id?: string;
  conversation_id?: string;
  persist?: boolean;
}): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/api/v1/assistant/chat", {
    ...body,
    stream: false,
  });
  return data;
}

export async function getAssistantConversations(
  vehicleId: string,
  limit = 20
): Promise<ConversationListResponse> {
  const { data } = await api.get<ConversationListResponse>(
    `/api/v1/assistant/conversations/${encodeURIComponent(vehicleId)}`,
    { params: { limit } }
  );
  return data;
}

export async function getAssistantConversationDetail(
  conversationId: string
): Promise<ConversationDetailResponse> {
  const { data } = await api.get<ConversationDetailResponse>(
    `/api/v1/assistant/conversations/detail/${encodeURIComponent(conversationId)}`
  );
  return data;
}

export type AssistantStreamHandlers = {
  onMeta?: (meta: AssistantSseMeta) => void;
  onToken?: (token: AssistantSseToken) => void;
  onDone?: (done: AssistantSseDone) => void;
};

/** Stream Module 5D SSE chat events via fetch (EventSource cannot POST). */
export async function chatAssistantStream(
  body: {
    message: string;
    vehicle_id?: string;
    driver_id?: string;
    conversation_id?: string;
    persist?: boolean;
  },
  handlers: AssistantStreamHandlers = {}
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, stream: true }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Assistant chat failed (${response.status})`);
  }
  if (!response.body) {
    throw new Error("Assistant stream body missing");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part
        .split("\n")
        .map((item) => item.trim())
        .find((item) => item.startsWith("data:"));
      if (!line) continue;
      const data = line.slice(5).trim();
      if (!data || data === "[DONE]") continue;
      try {
        const event = JSON.parse(data) as
          | AssistantSseMeta
          | AssistantSseToken
          | AssistantSseDone;
        if (event.type === "meta") handlers.onMeta?.(event);
        else if (event.type === "token") handlers.onToken?.(event);
        else if (event.type === "done") handlers.onDone?.(event);
      } catch {
        // ignore non-JSON SSE lines
      }
    }
  }
}
