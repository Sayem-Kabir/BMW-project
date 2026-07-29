# Spec Phase 10A / 13 — k6 WebSocket + HTTP dashboard load
# Usage:
#   k6 run scripts/load/ws_fleet_k6.js
#   k6 run -e VUS=500 -e DURATION=2m scripts/load/ws_fleet_k6.js
# Env: BASE_WS BASE_HTTP ORG_ID VUS DURATION

import http from "k6/http";
import ws from "k6/ws";
import { check, sleep } from "k6";

const VUS = Number(__ENV.VUS || 10);
const DURATION = __ENV.DURATION || "30s";

export const options = {
  vus: VUS,
  duration: DURATION,
  thresholds: {
    checks: ["rate>0.85"],
    http_req_duration: ["p(95)<300"],
  },
};

const BASE_WS = __ENV.BASE_WS || "ws://127.0.0.1:8001";
const BASE_HTTP = __ENV.BASE_HTTP || "http://127.0.0.1:8001";
const ORG_ID = __ENV.ORG_ID || "00000000-0000-4000-8000-000000000010";

export default function () {
  // HTTP health — dashboard-adjacent latency sample
  const health = http.get(`${BASE_HTTP}/health`);
  check(health, {
    "health 200": (r) => r.status === 200,
    "health p95 budget sample": (r) => r.timings.duration < 300,
  });

  const url = `${BASE_WS}/api/v1/fleet/ws/${ORG_ID}`;
  const res = ws.connect(url, {}, function (socket) {
    socket.on("open", function () {
      socket.setTimeout(function () {
        socket.close();
      }, 3000);
    });
    socket.on("error", function (e) {
      console.log("ws error", e);
    });
  });
  check(res, { "ws status 101": (r) => r && r.status === 101 });
  sleep(0.5);
}
