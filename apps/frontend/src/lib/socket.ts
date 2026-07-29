import { io, Socket } from "socket.io-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

let socket: Socket | null = null;

/** Socket.io client singleton — fleet WS native handler lands in Phase 6. */
export function getSocket(): Socket {
  if (!socket) {
    socket = io(API_URL, { autoConnect: false, path: "/socket.io" });
  }
  return socket;
}
