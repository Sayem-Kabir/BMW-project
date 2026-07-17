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
