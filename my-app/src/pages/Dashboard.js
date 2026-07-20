// import React from 'react';
 
// // ── Helper Functions ─────────────────────────────────────

// function formatUptime(seconds) {

//   if (!seconds) return '--';

//   const days  = Math.floor(seconds / 86400);

//   const hours = Math.floor((seconds % 86400) / 3600);

//   const mins  = Math.floor((seconds % 3600) / 60);

//   if (days > 0)  return `${days}d ${hours}h`;

//   if (hours > 0) return `${hours}h ${mins}m`;

//   return `${mins}m`;

// }
 
// function getProgressColor(value) {

//   if (value > 85) return 'var(--red)';

//   if (value > 65) return 'var(--yellow)';

//   return 'var(--accent)';

// }
 
// // ── Sub Components ───────────────────────────────────────

// function ProgressBar({ value }) {

//   const pct   = Math.min(100, Math.max(0, value || 0));

//   const color = getProgressColor(pct);

//   return (
// <div className="progress-bar">
// <div

//         className="progress-fill"

//         style={{ width: `${pct}%`, background: color }}

//       />
// </div>

//   );

// }
 
// function MetricCard({ label, value, unit, sub, color, showBar }) {

//   return (
// <div className={`metric-card ${color}`}>
// <div className="metric-label">{label}</div>
// <div className="metric-value">

//         {value ?? '--'}

//         {unit && <span className="metric-unit">{unit}</span>}
// </div>

//       {sub      && <div className="metric-sub">{sub}</div>}

//       {showBar  && <ProgressBar value={value} />}
// </div>

//   );

// }
 
// // ── Main Dashboard Component ─────────────────────────────

// export default function Dashboard({ status }) {
 
//   // Show loading state while waiting for first status fetch

//   if (!status) {

//     return (
// <div>
// <div className="page-header">
// <div>
// <div className="page-title">Dashboard</div>
// <div className="page-subtitle">Edge Collector overview</div>
// </div>
// </div>
// <div className="loading">
// <div className="spinner" />

//           Loading system status...
// </div>
// </div>

//     );

//   }
 
//   const {

//     system          = {},

//     devices         = [],

//     cloud_connected = false,

//     edge_id,

//     edge_name,

//     registered,

//     cloud_url,

//   } = status;
 
//   const onlineDevices  = devices.filter(d => d.status === 'online').length;

//   const offlineDevices = devices.filter(d => d.status === 'offline').length;
 
//   return (
// <div>
 
//       {/* ── Page Header ──────────────────────────────── */}
// <div className="page-header">
// <div>
// <div className="page-title">Dashboard</div>
// <div className="page-subtitle">

//             {system.hostname || 'Edge Collector'}
// &nbsp;·&nbsp;

//             {system.os || ''}

//             {edge_id && (
// <span style={{

//                 marginLeft:  12,

//                 fontFamily:  'var(--font-mono)',

//                 fontSize:    11,

//                 color:       'var(--text-muted)',

//               }}>

//                 Edge ID: {edge_id}
// </span>

//             )}
// </div>
// </div>
// </div>
 
//       {/* ── Cloud Not Connected Warning ───────────────── */}

//       {!cloud_connected && (
// <div className="alert warning">

//           ⚠ Not connected to cloud platform. Go to{' '}
// <strong>Settings</strong> and enter your Cloud URL and API Key.
// </div>

//       )}
 
//       {/* ── Cloud Connected But Not Registered ───────── */}

//       {cloud_connected && !registered && (
// <div className="alert info">

//           ◌ Connected to cloud. Waiting for registration confirmation...
// </div>

//       )}
 
//       {/* ── Metric Cards ─────────────────────────────── */}
// <div className="metrics-grid">
 
//         <MetricCard

//           label   = "Cloud Status"

//           value   = {cloud_connected ? 'Connected' : 'Offline'}

//           color   = {cloud_connected ? 'green' : 'red'}

//           sub     = {cloud_url

//             ? cloud_url.replace('https://', '').substring(0, 28) + '...'

//             : 'Not configured'}

//         />
 
//         <MetricCard

//           label   = "Total Devices"

//           value   = {devices.length}

//           color   = "blue"

//           sub     = {`${onlineDevices} online · ${offlineDevices} offline`}

//         />
 
//         <MetricCard

//           label   = "CPU Usage"

//           value   = {system.cpu_percent}

//           unit    = "%"

//           color   = "blue"

//           showBar = {true}

//           sub     = {`${system.cpu_count || '--'} cores`}

//         />
 
//         <MetricCard

//           label   = "Memory"

//           value   = {system.memory_percent}

//           unit    = "%"

//           color   = "yellow"

//           showBar = {true}

//           sub     = {`${system.memory_total_gb || '--'} GB total`}

//         />
 
//         <MetricCard

//           label   = "Disk Usage"

//           value   = {system.disk_percent}

//           unit    = "%"

//           color   = "blue"

//           showBar = {true}

//         />
 
//         <MetricCard

//           label = "Uptime"

//           value = {formatUptime(system.uptime_seconds)}

//           color = "green"

//           sub   = "System running"

//         />
 
//       </div>
 
//       {/* ── Device Status Table ───────────────────────── */}
// <div className="card">
// <div className="card-title">Device Status</div>
 
//         {devices.length === 0 ? (
// <div style={{

//             padding:    '20px 0',

//             textAlign:  'center',

//             fontFamily: 'var(--font-mono)',

//             fontSize:   12,

//             color:      'var(--text-muted)',

//           }}>

//             No devices assigned to this edge yet.<br />
// <span style={{ fontSize: 11, marginTop: 6, display: 'block' }}>

//               Devices are assigned from the Cloud Dashboard.
// </span>
// </div>

//         ) : (
// <table className="data-table">
// <thead>
// <tr>
// <th>Device Name</th>
// <th>Type</th>
// <th>IP Address</th>
// <th>Protocol</th>
// <th>Status</th>
// </tr>
// </thead>
// <tbody>

//               {devices.map(device => (
// <tr key={device.id}>
// <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>

//                     {device.name}
// </td>
// <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>

//                     {device.type}
// </td>
// <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>

//                     {device.ip_address}
// </td>
// <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>

//                     {device.protocol}
// </td>
// <td>
// <span className={`status-badge ${device.status || 'unknown'}`}>
// <span className={`status-dot ${device.status || 'unknown'}`} />

//                       {device.status || 'unknown'}
// </span>
// </td>
// </tr>

//               ))}
// </tbody>
// </table>

//         )}
// </div>
 
//       {/* ── Communication Flow Diagram ────────────────── */}
// <div className="card">
// <div className="card-title">Communication Flow</div>
// <div style={{

//           display:    'flex',

//           alignItems: 'center',

//           gap:        8,

//           flexWrap:   'wrap',

//           fontFamily: 'var(--font-mono)',

//           fontSize:   12,

//         }}>
 
//           {/* AV Devices */}
// <FlowBox

//             label = "AV Devices"

//             sub   = "LAN · TCP/RS232"

//             color = "var(--yellow)"

//           />
 
//           <FlowArrow label="TCP / RS232" />
 
//           {/* This Edge */}
// <FlowBox

//             label     = {edge_name || 'Edge Collector'}

//             sub       = "This PC/VM"

//             color     = "var(--accent)"

//             highlight = {true}

//           />
 
//           <FlowArrow label="HTTPS / WSS" />
 
//           {/* Cloud */}
// <FlowBox

//             label = "Cloud Platform"

//             sub   = {cloud_connected ? 'Connected ✓' : 'Disconnected ✗'}

//             color = {cloud_connected ? 'var(--green)' : 'var(--red)'}

//           />
 
//           <FlowArrow label="HTTPS" />
 
//           {/* Dashboard */}
// <FlowBox

//             label = "Web Dashboard"

//             sub   = "React UI"

//             color = "var(--text-secondary)"

//           />
 
//         </div>
 
//         {/* Flow explanation */}
// <div style={{

//           marginTop:  16,

//           padding:    '12px 16px',

//           background: 'var(--bg-base)',

//           borderRadius: 'var(--radius-sm)',

//           border:     '1px solid var(--border)',

//         }}>
// <div style={{

//             fontFamily: 'var(--font-mono)',

//             fontSize:   11,

//             color:      'var(--text-muted)',

//             lineHeight: 1.8,

//           }}>
// <div>

//               ▸ <span style={{ color: 'var(--text-secondary)' }}>

//                 Edge always initiates connection to cloud (outbound only)
// </span>
// </div>
// <div>

//               ▸ <span style={{ color: 'var(--text-secondary)' }}>

//                 Cloud sends command packets down through open WebSocket
// </span>
// </div>
// <div>

//               ▸ <span style={{ color: 'var(--text-secondary)' }}>

//                 Edge executes command on local AV device via TCP/RS232
// </span>
// </div>
// <div>

//               ▸ <span style={{ color: 'var(--text-secondary)' }}>

//                 Edge sends result back to cloud — cloud updates dashboard
// </span>
// </div>
// </div>
// </div>
// </div>
 
//     </div>

//   );

// }
 
// // ── Flow Diagram Sub Components ──────────────────────────

// function FlowBox({ label, sub, color, highlight }) {

//   return (
// <div style={{

//       padding:      '8px 14px',

//       background:   highlight ? 'var(--accent-glow)' : 'var(--bg-base)',

//       border:       `1px solid ${color}44`,

//       borderRadius: 'var(--radius-sm)',

//       borderLeft:   `3px solid ${color}`,

//       minWidth:     100,

//     }}>
// <div style={{ color, fontWeight: 600, fontSize: 12 }}>{label}</div>

//       {sub && (
// <div style={{ color: 'var(--text-muted)', fontSize: 10, marginTop: 2 }}>

//           {sub}
// </div>

//       )}
// </div>

//   );

// }
 
// function FlowArrow({ label }) {

//   return (
// <div style={{

//       display:    'flex',

//       flexDirection: 'column',

//       alignItems: 'center',

//       gap:        2,

//     }}>
// <div style={{ color: 'var(--text-muted)', fontSize: 16 }}>→</div>
// <div style={{ color: 'var(--text-muted)', fontSize: 9 }}>{label}</div>
// </div>

//   );

// }
 


import React from "react";

// ── Helper Functions ─────────────────────────────────────

function formatUptime(seconds) {
  if (!seconds) return "--";

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;

  return `${mins}m`;
}

function getProgressColor(value) {
  if (value > 85) return "var(--red)";
  if (value > 65) return "var(--yellow)";
  return "var(--accent)";
}

// ── Sub Components ───────────────────────────────────────

function ProgressBar({ value }) {
  const pct = Math.min(100, Math.max(0, value || 0));
  const color = getProgressColor(pct);

  return (
    <div className="progress-bar">
      <div
        className="progress-fill"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  );
}

function MetricCard({ label, value, unit, sub, color, showBar }) {
  return (
    <div className={`metric-card ${color}`}>
      <div className="metric-label">{label}</div>

      <div className="metric-value">
        {value ?? "--"}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>

      {sub && <div className="metric-sub">{sub}</div>}

      {showBar && <ProgressBar value={value} />}
    </div>
  );
}

// ── Main Dashboard Component ─────────────────────────────

export default function Dashboard({ status, statusError }) {
  if (statusError) {
    return (
      <div>
        <div className="page-header">
          <div>
            <div className="page-title">Dashboard</div>
            <div className="page-subtitle">Edge Collector overview</div>
          </div>
        </div>
        <div className="alert warning">
          Unable to load system status. {statusError}
        </div>
      </div>
    );
  }

  if (!status || typeof status !== "object") {
    return (
      <div className="loading">
        <div className="spinner" />
        Loading system status...
      </div>
    );
  }

  const {
    system = {},
    devices = [],
    cloud_connected = false,
    edge_id,
    edge_name,
    registered,
    cloud_url,
  } = status;

  const onlineDevices = devices.filter((d) => d?.status === "online").length;
  const offlineDevices = devices.filter((d) => d?.status === "offline").length;

  const cloudURLDisplay =
    typeof cloud_url === "string"
      ? cloud_url.replace("https://", "").substring(0, 28) + "..."
      : "Not configured";

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>

          <div className="page-subtitle">
            {system?.hostname || "Edge Collector"} · {system?.os || ""}

            {edge_id && (
              <span
                style={{
                  marginLeft: 12,
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--text-muted)",
                }}
              >
                Edge ID: {edge_id}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Cloud Warning */}
      {!cloud_connected && (
        <div className="alert warning">
          ⚠ Not connected to cloud platform. Go to <strong>Settings</strong>{" "}
          and enter your Cloud URL and API Key.
        </div>
      )}

      {cloud_connected && !registered && (
        <div className="alert info">
          ◌ Connected to cloud. Waiting for registration confirmation...
        </div>
      )}

      {/* Metrics */}
      <div className="metrics-grid">
        <MetricCard
          label="Cloud Status"
          value={cloud_connected ? "Connected" : "Offline"}
          color={cloud_connected ? "green" : "red"}
          sub={cloudURLDisplay}
        />

        <MetricCard
          label="Total Devices"
          value={devices.length}
          color="blue"
          sub={`${onlineDevices} online · ${offlineDevices} offline`}
        />

        <MetricCard
          label="CPU Usage"
          value={system?.cpu_percent}
          unit="%"
          color="blue"
          showBar={true}
          sub={`${system?.cpu_count || "--"} cores`}
        />

        <MetricCard
          label="Memory"
          value={system?.memory_percent}
          unit="%"
          color="yellow"
          showBar={true}
          sub={`${system?.memory_total_gb || "--"} GB total`}
        />

        <MetricCard
          label="Disk Usage"
          value={system?.disk_percent}
          unit="%"
          color="blue"
          showBar={true}
        />

        <MetricCard
          label="Uptime"
          value={formatUptime(system?.uptime_seconds)}
          color="green"
          sub="System running"
        />
      </div>

      {/* Device Table */}
      <div className="card">
        <div className="card-title">Device Status</div>

        {devices.length === 0 ? (
          <div
            style={{
              padding: "20px 0",
              textAlign: "center",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--text-muted)",
            }}
          >
            No devices assigned to this edge yet.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Device Name</th>
                <th>Type</th>
                <th>IP Address</th>
                <th>Protocol</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {devices.map((device, index) => (
                <tr key={device?.id || index}>
                  <td style={{ fontWeight: 500 }}>
                    {device?.name || "Unknown"}
                  </td>

                  <td>{device?.type || "--"}</td>

                  <td>{device?.ip_address || "--"}</td>

                  <td>{device?.protocol || "--"}</td>

                  <td>
                    <span
                      className={`status-badge ${device?.status || "unknown"}`}
                    >
                      {device?.status || "unknown"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
