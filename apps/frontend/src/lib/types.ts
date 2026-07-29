export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface FleetOverview {
  vehicle_count: number;
  active_alerts: number;
  average_risk: number;
  online_vehicles: number;
  risk_distribution?: Record<string, number>;
  phase?: string;
}

export interface FleetVehicleCard {
  id: string;
  name: string;
  vin?: string | null;
  model?: string | null;
  year?: number | null;
  fuel_type?: string | null;
  org_id?: string | null;
  is_active: boolean;
  risk_score: number;
  risk_level: RiskLevel | string;
  status: "operational" | "maintenance" | "critical" | string;
  active_alerts: number;
  worst_health?: number | null;
  latitude: number;
  longitude: number;
  phase?: string;
}

export interface FleetAlert {
  id: string;
  vehicle_id: string;
  driver_id?: string;
  event_type: string;
  severity: string;
  timestamp?: string | null;
  video_clip_url?: string | null;
  xai_explanation?: string | null;
  acknowledged?: boolean;
  latitude?: number | null;
  longitude?: number | null;
}

export interface LeaderboardEntry {
  rank: number;
  driver_id: string;
  name: string;
  email?: string;
  safety_score: number;
  risk_tier: "green" | "amber" | "red" | string;
  sparkline: number[];
  event_count_7d: number;
}

export interface IncidentWeek {
  week_start: string;
  total: number;
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
}

export interface XAIExplainResponse {
  explanation: string;
  method: string;
  heatmap_url?: string | null;
  ig_heatmap_url?: string | null;
  shap_values?: Record<string, unknown> | null;
  rule_trace?: Record<string, unknown> | null;
  activation_mass?: number | null;
  attribution?: string | null;
  phase: string;
}

export interface TelemetryHistoryResponse {
  vehicle_id: string;
  points: Array<{
    time: string;
    speed_kmh?: number | null;
    rpm?: number | null;
    battery_soc_pct?: number | null;
    tire_rl?: number | null;
    latitude?: number | null;
    longitude?: number | null;
  }>;
  phase?: string;
  source?: string;
}

export interface Vehicle {
  id: string;
  name: string;
  vin?: string | null;
  model?: string | null;
  year?: number | null;
  fuel_type?: string | null;
  is_active: boolean;
}

export interface HeadPose {
  pitch: number;
  yaw: number;
  roll: number;
  distracted?: boolean;
}

/** Payload from POST /api/v1/driver/analysis and WS stream. */
export interface DriverAnalysis {
  alertness_score: number;
  risk_level: RiskLevel;
  ear_value: number;
  mar_value: number;
  yawn_count?: number;
  head_pose: HeadPose;
  phone_detected: boolean;
  smoking_detected?: boolean;
  seatbelt_worn: boolean;
  is_drowsy?: boolean;
  is_yawning?: boolean;
  face_detected?: boolean;
  consecutive_drowsy_frames?: number;
  yolo_model_loaded?: boolean;
  vehicle_id?: string | null;
  session_id?: string | null;
  xai_heatmap_url?: string | null;
  phase?: string;
  message?: string;
}

/** Module 02 — cabin occupancy from POST /api/v1/cabin/analysis */
export interface CabinOccupancy {
  total_occupants: number;
  driver_present: boolean;
  front_passenger: boolean;
  rear_passengers: number;
  child_detected: boolean;
  child_alert: boolean;
  unattended_vehicle: boolean;
  occupant_map: Record<string, boolean>;
  persons: Array<{
    confidence: number;
    bbox: number[];
    seat_zone?: string | null;
    is_child: boolean;
  }>;
  model_loaded: boolean;
  message?: string | null;
  phase?: string;
}

export interface RoadObject {
  id: string;
  class: string;
  confidence: number;
  bbox: number[] | null;
  track_id: number | null;
  track_age_frames: number | null;
  track_hits: number | null;
  track_confirmed: boolean;
  relative_inverse_depth: number | null;
  distance_m: number | null;
  distance_calibrated: boolean;
  state: string | null;
  state_confidence: number | null;
  temporal_confidence: number | null;
  temporal_bbox: number[] | null;
  temporally_confirmed: boolean;
}

export interface RoadSegmentationSummary {
  model_loaded: boolean;
  weights_path: string | null;
  device: string | null;
  mask_shape: number[] | null;
  class_names: string[];
  class_ratios: Record<string, number>;
  mean_confidence: number | null;
  checkpoint_epoch: number | null;
  checkpoint_val_acc: number | null;
  message: string | null;
}

export interface RoadTrackingSummary {
  tracker_ready: boolean;
  frame_index: number;
  active_tracks: number;
  confirmed_tracks: number;
  min_hits: number;
  message: string | null;
}

export interface RoadDepthSummary {
  model_available: boolean;
  model_loaded: boolean;
  model_type: string;
  device: string | null;
  map_shape: number[] | null;
  inference_ms: number | null;
  metric_calibrated: boolean;
  message: string | null;
}

export interface RoadTrafficLightSummary {
  classifier_ready: boolean;
  states: string[];
  classified_count: number;
  known_count: number;
  message: string | null;
}

export interface RoadPedestrianTemporalSummary {
  model_loaded: boolean;
  weights_path: string | null;
  sequence_length: number;
  input_size: number;
  confidence_threshold: number;
  buffered_frames: number;
  detected: boolean;
  confidence: number | null;
  bbox: number[] | null;
  message: string | null;
}

export interface RoadPipelineSummary {
  processing_ms: number;
  stage_times_ms: Record<string, number>;
  warnings: string[];
}

/** Payload from Module 2H REST analysis and WebSocket streaming. */
export interface RoadAnalysis {
  objects: RoadObject[];
  segmentation: RoadSegmentationSummary | null;
  tracking: RoadTrackingSummary | null;
  depth: RoadDepthSummary | null;
  traffic_lights: RoadTrafficLightSummary | null;
  pedestrian_temporal: RoadPedestrianTemporalSummary | null;
  pipeline: RoadPipelineSummary | null;
  stream_id: string | null;
  frame_id: number;
  timestamp: string;
  phase: string;
  message: string;
}

export type MaintenanceComponent = "engine" | "brake" | "battery" | "tire";
export type MaintenanceSeverity = "normal" | "warning" | "critical" | "unknown";
export type MaintenanceComponentStatus = "ok" | "unavailable" | "error";

export interface MaintenanceFeatureContribution {
  feature: string;
  value: number;
  contribution: number;
  direction: "increases_risk" | "decreases_risk";
}

export interface MaintenanceExplanation {
  output_index: number;
  base_value: number;
  top_features: MaintenanceFeatureContribution[];
  method: string;
}

export interface MaintenanceComponentSummary {
  component: MaintenanceComponent;
  status: MaintenanceComponentStatus;
  severity: MaintenanceSeverity | null;
  health_score: number | null;
  maintenance_required: boolean | null;
  confidence: number | null;
  result: Record<string, unknown> | null;
  explanation: MaintenanceExplanation | null;
  explanation_error: string | null;
  missing_features: string[];
  error: string | null;
  latency_ms: number;
}

export interface MaintenanceAlert {
  component: MaintenanceComponent;
  severity: MaintenanceSeverity;
  message: string;
}

export interface MaintenanceRunResponse {
  vehicle_id: string;
  status: "complete" | "partial" | "failed";
  overall_severity: MaintenanceSeverity;
  timestamp: string;
  components: Record<MaintenanceComponent, MaintenanceComponentSummary>;
  alerts: MaintenanceAlert[];
  warnings: string[];
  processing_ms: number;
  stage_times_ms: Record<string, number>;
  persisted: number;
  ml_model_version: string;
  phase: string;
}

export interface MaintenancePrediction {
  id: string | null;
  vehicle_id: string;
  component: MaintenanceComponent;
  health_score: number;
  anomaly_score: number | null;
  predicted_replacement_date: string | null;
  predicted_remaining_km: number | null;
  confidence: number | null;
  shap_explanation: {
    severity?: MaintenanceSeverity;
    maintenance_required?: boolean;
    result?: Record<string, unknown>;
    explanation?: MaintenanceExplanation | null;
    explanation_error?: string | null;
  } | null;
  ml_model_version: string | null;
  created_at: string | null;
}

export interface MaintenanceStatus {
  components: Record<
    MaintenanceComponent,
    { model_ready: boolean; required_features: string[] }
  >;
  all_models_ready: boolean;
  ml_model_version: string;
  phase: string;
}

export interface MaintenanceLatestResponse {
  vehicle_id: string;
  predictions: MaintenancePrediction[];
  phase: string;
}

export interface MaintenanceHistoryResponse {
  vehicle_id: string;
  history: MaintenancePrediction[];
  phase: string;
}

export interface RiskFactor {
  key: string;
  label: string;
  weight: number;
  contribution: number;
  reason: string;
  evidence: Record<string, unknown>;
}

export interface RiskOverride {
  rule_id: string;
  reason: string;
  previous_score: number;
  resulting_score: number;
  previous_level: string;
  resulting_level: string;
  evidence: Record<string, unknown>;
}

export interface RiskScore {
  vehicle_id: string;
  score: number;
  level: RiskLevel;
  risk_score?: number;
  risk_level?: RiskLevel;
  factors: RiskFactor[];
  reasons: string[];
  overrides: RiskOverride[];
  base_score?: number | null;
  base_level?: RiskLevel | null;
  timestamp: string;
  method?: string | null;
  phase?: string;
  message?: string | null;
}

export interface RiskComputeResponse extends RiskScore {
  published: boolean;
  receivers: number;
  cached: boolean;
  persisted: boolean;
  record_id?: string | null;
  warning?: string | null;
  persist_warning?: string | null;
}

export interface RiskHistoryItem {
  id: string;
  vehicle_id: string;
  score: number;
  level: RiskLevel;
  timestamp: string;
  factors: RiskFactor[];
  reasons: string[];
  overrides: RiskOverride[];
}

export interface RiskHistoryResponse {
  vehicle_id: string;
  history: RiskHistoryItem[];
  count: number;
  phase: string;
  warning?: string | null;
}

export interface SafetyEvent {
  id: string;
  vehicle_id: string;
  driver_id: string;
  session_id?: string | null;
  event_type: string;
  severity: RiskLevel;
  timestamp: string;
  latitude?: number | null;
  longitude?: number | null;
  telemetry_snapshot?: Record<string, unknown> | null;
  video_clip_url?: string | null;
  xai_explanation?: string | null;
  acknowledged: boolean;
  acknowledged_at?: string | null;
}

export interface EventListResponse {
  vehicle_id: string;
  events: SafetyEvent[];
  count: number;
  phase: string;
  warning?: string | null;
}

export interface EventDetectResponse {
  vehicle_id: string;
  driver_id: string;
  session_id?: string | null;
  detected: number;
  persisted: number;
  events: Array<{
    id: string;
    event_type: string;
    severity: RiskLevel;
    timestamp: string;
    video_clip_url?: string | null;
    xai_explanation?: string | null;
  }>;
  warnings: string[];
  skipped_detectors: string[];
  completed_at: string;
  phase: string;
}

export interface FleetRiskWebSocketMessage {
  type:
    | "connected"
    | "risk_update"
    | "safety_event"
    | "maintenance_alert"
    | "pong"
    | "error";
  data?: RiskScore & Record<string, unknown>;
  channel?: string;
  org_id?: string;
  phase?: string;
  message?: string;
  detail?: string;
  timestamp?: string;
  patterns?: string[];
}

export interface ChatResponse {
  conversation_id?: string | null;
  vehicle_id?: string | null;
  message: string;
  reply: string;
  intent: string;
  route: string;
  citations: string[];
  obd_matches: Array<Record<string, string>>;
  telemetry_context?: string | null;
  maintenance_context?: string | null;
  conversation_memory?: string | null;
  memory_message_count?: number;
  llm_backend?: string | null;
  llm_model?: string | null;
  warnings: string[];
  phase: string;
}

export interface ConversationDetailResponse {
  id: string;
  vehicle_id?: string | null;
  driver_id?: string | null;
  started_at: string;
  messages: Array<{ role?: string; content?: string; [key: string]: unknown }>;
  phase: string;
}

export interface ConversationSummary {
  id: string;
  vehicle_id?: string | null;
  driver_id?: string | null;
  started_at: string;
  message_count: number;
  last_user_message?: string | null;
  last_assistant_message?: string | null;
}

export interface ConversationListResponse {
  vehicle_id: string;
  conversations: ConversationSummary[];
  count: number;
  phase: string;
  warning?: string | null;
}

export interface AssistantSseMeta {
  type: "meta";
  conversation_id?: string | null;
  vehicle_id?: string | null;
  intent?: string;
  route?: string;
  citations?: string[];
  llm_backend?: string | null;
  llm_model?: string | null;
  maintenance_context?: string | null;
  memory_message_count?: number;
  warnings?: string[];
  phase?: string;
}

export interface AssistantSseToken {
  type: "token";
  text: string;
}

export interface AssistantSseDone {
  type: "done";
  reply?: string;
  conversation_id?: string | null;
  phase?: string;
}

