import React, { useState, useEffect } from "react";
import Dashboard from "./pages/Dashboard";
import Devices from "./pages/Devices";
import Settings from "./pages/Settings";
import Logs from "./pages/Logs";
import { statusAPI } from "./services/api";
import "./App.css";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "⬡" },
  { id: "devices", label: "Devices", icon: "◈" },
  { id: "settings", label: "Settings", icon: "◎" },
  { id: "logs", label: "Logs", icon: "≡" },
];

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [status, setStatus] = useState(null);
  const [cloudOnline, setCloudOnline] = useState(false);
  const [statusError, setStatusError] = useState(null);

  // ── Poll /api/status every 10 seconds ─────────────────
  useEffect(() => {
    let interval;

    const fetchStatus = async () => {
      try {
        const res = await statusAPI.getStatus();
        const data = res?.data;

        if (data && typeof data === "object" && !Array.isArray(data)) {
          setStatus(data);
          setCloudOnline(data.cloud_connected || false);
          setStatusError(null);
        } else {
          setStatus(null);
          setCloudOnline(false);
          setStatusError(
            "Unexpected response from /api/status/. The API may be unreachable or proxying to the React dev server."
          );
        }
      } catch (err) {
        console.error("Status fetch failed:", err);
        setStatus(null);
        setCloudOnline(false);
        setStatusError(err?.message || "Status fetch failed.");
      }
    };

    fetchStatus();
    interval = setInterval(fetchStatus, 10000);

    return () => clearInterval(interval);
  }, []);

  const deviceCount = status?.devices?.length || 0;

  const onlineCount =
    status?.devices?.filter((d) => d.status === "online").length || 0;

  return (
    <div className="app">
      {/* ── Sidebar ───────────────────────── */}
      <aside className="sidebar">
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="brand-icon">EC</div>
          <div>
            <div className="brand-name">Edge Collector</div>
            <div className="brand-version">v1.0.0</div>
          </div>
        </div>

        {/* Cloud Status */}
        <div
          className={`cloud-badge ${
            cloudOnline ? "connected" : "disconnected"
          }`}
        >
          <span
            className={`pulse-dot ${cloudOnline ? "online" : "offline"}`}
          />
          <span className="badge-label">
            {cloudOnline ? "Cloud Connected" : "Cloud Offline"}
          </span>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${
                activePage === item.id ? "active" : ""
              }`}
              onClick={() => setActivePage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Footer Stats */}
        <div className="sidebar-footer">
          <div className="footer-stat">
            <span className="footer-stat-label">Devices</span>
            <span className="footer-stat-value">
              {onlineCount}/{deviceCount}
            </span>
          </div>

          {status?.system && (
            <>
              <div className="footer-stat">
                <span className="footer-stat-label">CPU</span>
                <span className="footer-stat-value">
                  {status.system?.cpu_percent ?? 0}%
                </span>
              </div>

              <div className="footer-stat">
                <span className="footer-stat-label">RAM</span>
                <span className="footer-stat-value">
                  {status.system?.memory_percent ?? 0}%
                </span>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* ── Main Content ───────────────────── */}
      <main className="main-content">
        {activePage === "dashboard" && (
          <Dashboard status={status} statusError={statusError} />
        )}
        {activePage === "devices" && <Devices />}
        {activePage === "settings" && <Settings />}
        {activePage === "logs" && <Logs />}
      </main>
    </div>
  );
}
