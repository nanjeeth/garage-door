import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import type { DoorStatus, DoorEvent } from "../api";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function actionIcon(action: string): string {
  switch (action) {
    case "open": return "🔓";
    case "close": return "🔒";
    case "trigger": return "👆";
    default: return "📋";
  }
}

function sourceLabel(source: string): string {
  switch (source) {
    case "api": return "App";
    case "auto": return "Auto";
    case "esp32": return "Sensor";
    case "manual": return "Manual";
    default: return source;
  }
}

export default function Dashboard() {
  const queryClient = useQueryClient();

  const { data: status, isLoading: statusLoading } = useQuery<DoorStatus>({
    queryKey: ["status"],
    queryFn: api.status,
  });

  const { data: events = [], isLoading: eventsLoading } = useQuery<DoorEvent[]>({
    queryKey: ["events"],
    queryFn: () => api.events(20),
  });

  const triggerMutation = useMutation({
    mutationFn: api.trigger,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["status"] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
    },
  });

  const autoOpenMutation = useMutation({
    mutationFn: (enabled: boolean) => api.toggleAutoOpen(enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["status"] });
    },
  });

  if (statusLoading) {
    return <div className="loading">Connecting to garage...</div>;
  }

  if (!status) {
    return <div className="error">Could not connect to server</div>;
  }

  return (
    <div className="dashboard">
      {/* Door Status Card */}
      <div className={`door-card ${status.is_open ? "open" : "closed"}`}>
        <div className="door-icon">{status.is_open ? "🔓" : "🔒"}</div>
        <div className="door-status">
          <h2>{status.is_open ? "OPEN" : "CLOSED"}</h2>
          {status.last_changed && (
            <p className="last-changed">
              {timeAgo(status.last_changed)}
            </p>
          )}
        </div>
        <div className={`esp32-badge ${status.esp32_reachable ? "online" : "offline"}`}>
          {status.esp32_reachable ? "● Online" : "● Offline"}
        </div>
      </div>

      {/* Controls */}
      <div className="controls">
        <button
          className="trigger-btn"
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending || !status.esp32_reachable}
        >
          {triggerMutation.isPending ? "Triggering..." : status.is_open ? "Close Door" : "Open Door"}
        </button>

        <div className="auto-open-toggle">
          <label className="toggle-label">
            <span>Auto-open on arrival</span>
            <div
              className={`toggle ${status.auto_open_enabled ? "on" : "off"}`}
              onClick={() => autoOpenMutation.mutate(!status.auto_open_enabled)}
            >
              <div className="toggle-knob" />
            </div>
          </label>
        </div>
      </div>

      {/* Event History */}
      <div className="events-section">
        <h3>Recent Activity</h3>
        {eventsLoading ? (
          <p className="loading">Loading events...</p>
        ) : events.length === 0 ? (
          <p className="no-events">No events yet</p>
        ) : (
          <div className="events-list">
            {events.map((event) => (
              <div key={event.id} className="event-row">
                <span className="event-icon">{actionIcon(event.action)}</span>
                <div className="event-info">
                  <span className="event-action">
                    Door {event.action === "trigger" ? "triggered" : event.action === "open" ? "opened" : "closed"}
                  </span>
                  <span className="event-meta">
                    {formatTime(event.timestamp)}
                    <span className={`source-badge ${event.source}`}>
                      {sourceLabel(event.source)}
                    </span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
