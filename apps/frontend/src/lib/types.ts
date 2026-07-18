export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface FleetOverview {
  vehicle_count: number;
  active_alerts: number;
  average_risk: number;
  online_vehicles: number;
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
