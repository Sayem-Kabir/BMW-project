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

export interface DriverAnalysis {
  alertness_score: number;
  risk_level: RiskLevel;
  ear_value: number;
  mar_value: number;
  phone_detected: boolean;
  seatbelt_worn: boolean;
}
