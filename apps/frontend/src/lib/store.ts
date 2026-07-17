import { create } from "zustand";
import type { FleetOverview } from "./types";

interface AppState {
  fleetOverview: FleetOverview | null;
  setFleetOverview: (overview: FleetOverview | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  fleetOverview: null,
  setFleetOverview: (fleetOverview) => set({ fleetOverview }),
}));
