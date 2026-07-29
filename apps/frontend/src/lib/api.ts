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

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

/** Bearer header for raw `fetch` calls (axios interceptor does not apply). */
function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

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

export async function getFleetOverviewDetail(orgId?: string) {
  const { data } = await api.get("/api/v1/fleet/overview/detail", {
    params: orgId ? { org_id: orgId } : undefined,
  });
  return data;
}

export async function getFleetVehicles(orgId?: string) {
  const { data } = await api.get("/api/v1/fleet/vehicles", {
    params: orgId ? { org_id: orgId } : undefined,
  });
  return data as { vehicles: import("@/lib/types").FleetVehicleCard[]; count: number; phase: string };
}

export async function getFleetAlerts(orgId?: string, limit = 50) {
  const { data } = await api.get("/api/v1/fleet/alerts", {
    params: { limit, ...(orgId ? { org_id: orgId } : {}) },
  });
  return data as { alerts: import("@/lib/types").FleetAlert[]; count: number; phase: string };
}

export async function acknowledgeFleetAlert(alertId: string) {
  const { data } = await api.post(
    `/api/v1/fleet/alerts/${encodeURIComponent(alertId)}/acknowledge`
  );
  return data;
}

export async function login(
  email: string,
  password: string,
  totpCode?: string
) {
  const { data } = await api.post("/api/v1/auth/login", {
    email,
    password,
    totp_code: totpCode || null,
  });
  const result = data as {
    access_token: string;
    refresh_token?: string;
    token_type: string;
    mfa_required?: boolean;
    mfa_token?: string;
  };
  if (result?.mfa_required) {
    return result;
  }
  if (typeof window !== "undefined" && result?.access_token) {
    localStorage.setItem("access_token", result.access_token);
    if (result.refresh_token) {
      localStorage.setItem("refresh_token", result.refresh_token);
    }
  }
  return result;
}

export async function completeMfa(mfaToken: string, totpCode: string) {
  const { data } = await api.post("/api/v1/auth/mfa/complete", {
    mfa_token: mfaToken,
    totp_code: totpCode,
  });
  if (typeof window !== "undefined" && data?.access_token) {
    localStorage.setItem("access_token", data.access_token);
    if (data.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
  }
  return data;
}

export async function verifyEmail(token: string) {
  const { data } = await api.post("/api/v1/auth/verify-email", { token });
  return data;
}

export async function requestPasswordReset(email: string) {
  const { data } = await api.post("/api/v1/auth/forgot-password", { email });
  return data as { status: string; reset_token?: string };
}

export async function resetPassword(token: string, newPassword: string) {
  const { data } = await api.post("/api/v1/auth/reset-password", {
    token,
    new_password: newPassword,
  });
  return data;
}

export async function getGoogleAuthUrl() {
  const { data } = await api.get("/api/v1/auth/google/authorize");
  return data as { authorization_url: string };
}

export async function exchangeGoogleCode(code: string) {
  const { data } = await api.post("/api/v1/auth/google/exchange", { code });
  if (typeof window !== "undefined" && data?.access_token) {
    localStorage.setItem("access_token", data.access_token);
    if (data.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
  }
  return data;
}

export async function enableMfa() {
  const { data } = await api.post("/api/v1/auth/mfa/enable");
  return data as { secret: string; otpauth_url: string };
}

export async function confirmMfa(totpCode: string) {
  const { data } = await api.post("/api/v1/auth/mfa/confirm", {
    totp_code: totpCode,
  });
  return data;
}

export async function disableMfa(totpCode: string) {
  const { data } = await api.post("/api/v1/auth/mfa/disable", {
    totp_code: totpCode,
  });
  return data;
}

export async function registerAccount(body: {
  email: string;
  password: string;
  full_name?: string;
  org_name?: string;
}) {
  const { data } = await api.post("/api/v1/auth/register", body);
  return data;
}

export async function createOnboardingOrg(orgName: string) {
  const { data } = await api.post("/api/v1/auth/onboarding/org", {
    org_name: orgName,
  });
  return data;
}

export async function getAdminAudit(limit = 50) {
  const { data } = await api.get("/api/v1/admin/audit", { params: { limit } });
  return data as {
    items: Array<{
      id: string;
      action: string;
      target_type?: string | null;
      created_at?: string | null;
      metadata?: Record<string, unknown> | null;
    }>;
    count: number;
  };
}

export async function getAdminHealth() {
  const { data } = await api.get("/api/v1/admin/health");
  return data as {
    environment: string;
    database: string;
    redis: string;
    metrics_endpoint: string;
    ready_endpoint: string;
  };
}

export async function listOrgUsers(orgId: string) {
  const { data } = await api.get(`/api/v1/orgs/${orgId}/users`);
  return data as Array<{
    id: string;
    email: string;
    role: string;
    full_name?: string | null;
  }>;
}

export async function inviteOrgUser(
  orgId: string,
  body: { email: string; role: string; full_name?: string }
) {
  const { data } = await api.post(`/api/v1/orgs/${orgId}/users/invite`, body);
  return data;
}

export async function changeUserRole(userId: string, role: string) {
  const { data } = await api.patch(`/api/v1/orgs/users/${userId}/role`, { role });
  return data;
}

export async function logout() {
  const refresh =
    typeof window !== "undefined"
      ? localStorage.getItem("refresh_token")
      : null;
  try {
    await api.post("/api/v1/auth/logout", { refresh_token: refresh });
  } catch {
    /* ignore */
  }
  if (typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    const { clearRoleCookie } = await import("@/lib/roles");
    clearRoleCookie();
  }
}

export async function getMe() {
  const { data } = await api.get("/api/v1/auth/me");
  return data as {
    id: string;
    email: string;
    full_name?: string | null;
    role: string;
    org_id?: string | null;
    driver_id?: string | null;
    is_email_verified?: boolean;
    mfa_enabled?: boolean;
  };
}

export async function getDemoStatus() {
  const { data } = await api.get("/api/v1/demo/status");
  return data as {
    running: boolean;
    status?: string;
    frames_sent?: number;
    last_error?: string | null;
    started_at?: string | null;
    vehicle_id?: string;
    phase?: string;
    pid?: number | null;
  };
}

export async function startDemo(body?: {
  vehicle_id?: string;
  fps?: number;
  synthetic_only?: boolean;
  loop?: boolean;
  max_frames?: number;
}) {
  const { data } = await api.post("/api/v1/demo/start", body ?? {});
  return data;
}

export async function stopDemo() {
  const { data } = await api.post("/api/v1/demo/stop");
  return data;
}

export async function getFleetLeaderboard(orgId?: string, days = 7) {
  const { data } = await api.get("/api/v1/analytics/fleet/leaderboard", {
    params: { days, ...(orgId ? { org_id: orgId } : {}) },
  });
  return data as {
    leaderboard: import("@/lib/types").LeaderboardEntry[];
    count: number;
    phase: string;
  };
}

export async function getFleetIncidents(orgId?: string, weeks = 8) {
  const { data } = await api.get("/api/v1/analytics/fleet/incidents", {
    params: { weeks, ...(orgId ? { org_id: orgId } : {}) },
  });
  return data as {
    incidents: import("@/lib/types").IncidentWeek[];
    count: number;
    phase: string;
  };
}

export async function getTelemetryHistory(vehicleId: string) {
  const { data } = await api.get(
    `/api/v1/telemetry/${encodeURIComponent(vehicleId)}`
  );
  return data as import("@/lib/types").TelemetryHistoryResponse;
}

export async function explainXai(body: {
  event_id?: string;
  event_type?: string;
  component?: string;
  vehicle_id?: string;
}) {
  const { data } = await api.post("/api/v1/xai/explain", body);
  return data as import("@/lib/types").XAIExplainResponse;
}

export async function explainXaiFrame(
  file: Blob,
  eventType = "drowsiness",
  filename = "frame.jpg",
  attribution: "gradcam" | "ig" | "both" = "gradcam"
) {
  const form = new FormData();
  form.append("file", file, filename);
  form.append("event_type", eventType);
  form.append("attribution", attribution);
  const response = await fetch(`${API_URL}/api/v1/xai/explain/frame`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `XAI frame explain failed (${response.status})`);
  }
  return (await response.json()) as import("@/lib/types").XAIExplainResponse;
}

export function xaiHeatmapUrl(pathOrFilename: string): string {
  if (pathOrFilename.startsWith("http")) return pathOrFilename;
  if (pathOrFilename.startsWith("/api/")) return `${API_URL}${pathOrFilename}`;
  return `${API_URL}/api/v1/xai/heatmap/${encodeURIComponent(pathOrFilename)}`;
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
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Analysis failed (${res.status})`);
  }
  return res.json() as Promise<DriverAnalysis>;
}

/** Module 02 cabin occupancy analysis. */
export async function analyzeCabinFrame(
  file: Blob,
  filename = "cabin-frame.jpg"
): Promise<import("@/lib/types").CabinOccupancy> {
  const form = new FormData();
  form.append("file", file, filename);
  const res = await fetch(`${API_URL}/api/v1/cabin/analysis`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Cabin analysis failed (${res.status})`);
  }
  return res.json() as Promise<import("@/lib/types").CabinOccupancy>;
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
    headers: authHeaders(),
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
    { method: "DELETE", headers: authHeaders() }
  );
  if (!res.ok) {
    throw new Error(`Could not reset road stream (${res.status})`);
  }
  const payload = (await res.json()) as { reset?: boolean };
  return Boolean(payload.reset);
}

export async function getRoadStatus(): Promise<RoadAnalysis> {
  const res = await fetch(`${API_URL}/api/v1/road/status`, {
    headers: authHeaders(),
  });
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

/** Turn `minio://bucket/key` into an HTTP media URL (CDN / MinIO public / console). */
export function clipLink(url: string | null | undefined): {
  href: string | null;
  label: string;
} {
  if (!url) {
    return { href: null, label: "No clip stored" };
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return { href: url, label: url };
  }
  if (url.startsWith("minio://")) {
    const rest = url.slice("minio://".length);
    const slash = rest.indexOf("/");
    if (slash > 0) {
      const bucket = rest.slice(0, slash);
      const object = rest.slice(slash + 1);
      const cdn = process.env.NEXT_PUBLIC_CDN_BASE_URL;
      if (cdn) {
        return {
          href: `${cdn.replace(/\/$/, "")}/${bucket}/${object}`,
          label: url,
        };
      }
      const minioPublic =
        process.env.NEXT_PUBLIC_MINIO_PUBLIC_URL || "http://localhost:9000";
      return {
        href: `${minioPublic.replace(/\/$/, "")}/${bucket}/${object}`,
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

function emitChatAsStream(
  data: ChatResponse,
  handlers: AssistantStreamHandlers
): void {
  handlers.onMeta?.({
    type: "meta",
    conversation_id: data.conversation_id ? String(data.conversation_id) : null,
    vehicle_id: data.vehicle_id ? String(data.vehicle_id) : null,
    intent: data.intent,
    route: data.route,
    citations: data.citations || [],
    llm_backend: data.llm_backend,
    llm_model: data.llm_model,
    maintenance_context: data.maintenance_context,
    memory_message_count: data.memory_message_count || 0,
    warnings: data.warnings || [],
    phase: data.phase,
  });
  const reply = data.reply || "";
  if (reply) handlers.onToken?.({ type: "token", text: reply });
  handlers.onDone?.({
    type: "done",
    reply,
    conversation_id: data.conversation_id
      ? String(data.conversation_id)
      : null,
    phase: data.phase,
  });
}

/** Chat via authenticated axios (JSON). SSE fetch kept as optional fast-path. */
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
  // Always use axios so the Bearer token from the login interceptor is sent.
  // (Raw fetch previously hit 401 "Authentication required" even when history
  // GETs worked, because it skipped the axios auth interceptor.)
  const data = await chatAssistant(body);
  emitChatAsStream(data, handlers);
}
