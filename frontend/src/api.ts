const BASE = import.meta.env.DEV ? "http://localhost:8002" : "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export interface DoorStatus {
  is_open: boolean;
  last_changed: string | null;
  last_triggered: string | null;
  esp32_reachable: boolean;
  esp32_status: string | null;
  auto_open_enabled: boolean;
}

export interface DoorEvent {
  id: number;
  action: string;
  source: string;
  timestamp: string;
}

export const api = {
  status: () => request<DoorStatus>("/api/door/status"),
  trigger: () => request<{ success: boolean }>("/api/door/trigger", { method: "POST" }),
  events: (limit = 50) => request<DoorEvent[]>(`/api/door/events?limit=${limit}`),
  toggleAutoOpen: (enabled: boolean) =>
    request<{ auto_open_enabled: boolean }>(`/api/door/auto-open/${enabled}`, { method: "POST" }),
};
