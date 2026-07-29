"use client";

import { useEffect, useRef } from "react";
import type { FleetVehicleCard } from "@/lib/types";

interface Props {
  vehicles: FleetVehicleCard[];
}

type LeafletNS = typeof import("leaflet");

type LeafletMap = {
  remove: () => void;
  stop: () => void;
  off: () => void;
  fitBounds: (
    bounds: [number, number][],
    opts?: { padding?: [number, number]; animate?: boolean }
  ) => void;
  invalidateSize: () => void;
};

type MarkerLayer = {
  clearLayers: () => void;
  addLayer: (l: unknown) => void;
};

function syncMarkers(
  L: LeafletNS,
  map: LeafletMap,
  layer: MarkerLayer,
  vehicles: FleetVehicleCard[]
) {
  layer.clearLayers();

  vehicles.forEach((vehicle) => {
    const color =
      vehicle.status === "critical"
        ? "#ef4444"
        : vehicle.status === "maintenance"
          ? "#f59e0b"
          : "#22c55e";
    const marker = L.circleMarker([vehicle.latitude, vehicle.longitude], {
      radius: 8,
      color: "#0f172a",
      weight: 1,
      fillColor: color,
      fillOpacity: 0.9,
    });
    marker.bindPopup(
      `<strong>${vehicle.name}</strong><br/>Risk ${vehicle.risk_score} (${vehicle.risk_level})`
    );
    layer.addLayer(marker);
  });

  if (vehicles.length) {
    try {
      map.fitBounds(
        vehicles.map((v) => [v.latitude, v.longitude] as [number, number]),
        { padding: [30, 30], animate: false }
      );
    } catch {
      /* container may be mid-unmount */
    }
  }
}

/** Leaflet map via dynamic import to avoid SSR issues. */
export function FleetMap({ vehicles }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const leafletRef = useRef<LeafletNS | null>(null);
  const markersLayerRef = useRef<MarkerLayer | null>(null);
  const vehiclesRef = useRef(vehicles);
  vehiclesRef.current = vehicles;

  // Create map once
  useEffect(() => {
    let cancelled = false;

    async function setup() {
      if (!containerRef.current || mapRef.current) return;
      const L = await import("leaflet");
      if (cancelled || !containerRef.current || mapRef.current) return;

      leafletRef.current = L;

      if (!document.getElementById("leaflet-css")) {
        const link = document.createElement("link");
        link.id = "leaflet-css";
        link.rel = "stylesheet";
        link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        document.head.appendChild(link);
      }

      // Avoid "Map container is already initialized" on Strict Mode remount
      containerRef.current.innerHTML = "";

      const map = L.map(containerRef.current, {
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false,
      }).setView([48.1351, 11.582], 12);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap",
        maxZoom: 18,
      }).addTo(map);

      const layer = L.layerGroup().addTo(map);
      markersLayerRef.current = layer;
      mapRef.current = map;

      syncMarkers(L, map, layer, vehiclesRef.current);

      requestAnimationFrame(() => {
        if (!cancelled && mapRef.current) {
          try {
            mapRef.current.invalidateSize();
          } catch {
            /* map already torn down */
          }
        }
      });
    }

    void setup();

    return () => {
      cancelled = true;
      const map = mapRef.current;
      mapRef.current = null;
      markersLayerRef.current = null;
      if (map) {
        try {
          map.stop();
          map.off();
          map.remove();
        } catch {
          /* ignore teardown races */
        }
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, []);

  // Sync markers when vehicle list changes (do not recreate the map)
  useEffect(() => {
    const map = mapRef.current;
    const L = leafletRef.current;
    const layer = markersLayerRef.current;
    if (!map || !L || !layer) return;
    syncMarkers(L, map, layer, vehicles);
  }, [vehicles]);

  return (
    <div
      ref={containerRef}
      className="h-72 w-full overflow-hidden rounded-xl border border-slate-800"
    />
  );
}
