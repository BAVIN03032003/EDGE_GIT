import React, { useState, useEffect, useCallback } from 'react';

import { devicesAPI, commandAPI } from '../services/api';
 
// ── Test Command Form ────────────────────────────────────

function TestCommandPanel() {

  const [form, setForm]       = useState({

    ip_address:       '',

    port:             '1515',

    protocol:         'tcp',

    payload_type:     'hex',

    payload_data:     'AA 11 01 00 11',

    timeout:          '5',

    expect_response:  true,

  });

  const [loading,  setLoading]  = useState(false);

  const [result,   setResult]   = useState(null);
 
  const update = (key, value) =>

    setForm(prev => ({ ...prev, [key]: value }));
 
  const handleTest = async () => {

    setLoading(true);

    setResult(null);
 
    const packet = {

      command_id:  `test_${Date.now()}`,

      device_name: 'Manual Test',

      connection: {

        protocol:        form.protocol,

        ip_address:      form.ip_address,

        port:            parseInt(form.port),

        timeout:         parseInt(form.timeout),

        expect_response: form.expect_response,

      },

      payload: {

        type: form.payload_type,

        data: form.payload_data,

      },

    };
 
    try {

      const res = await commandAPI.testCommand(packet);

      setResult({

        type:    res.data.success ? 'success' : 'error',

        data:    res.data,

      });

    } catch (err) {

      setResult({

        type:    'error',

        data:    { error: err.response?.data?.error || 'Request failed' },

      });

    } finally {

      setLoading(false);

    }

  };
 
  return (
<div className="card">
<div className="card-title">Test Raw Command (Local)</div>
<p style={{

        fontSize:     13,

        color:        'var(--text-secondary)',

        marginBottom: 16,

        lineHeight:   1.6,

      }}>

        Send a raw command directly to a device on your local network.

        Use this to verify a device is reachable before connecting to cloud.
</p>
 
      <div className="grid-2">
<div>
<div className="form-group">
<label className="form-label">Device IP Address</label>
<input

              className = "form-input"

              type      = "text"

              placeholder = "192.168.1.10"

              value     = {form.ip_address}

              onChange  = {e => update('ip_address', e.target.value)}

            />
</div>
 
          <div className="form-group">
<label className="form-label">Port</label>
<input

              className   = "form-input"

              type        = "number"

              placeholder = "1515"

              value       = {form.port}

              onChange    = {e => update('port', e.target.value)}

            />
</div>
 
          <div className="form-group">
<label className="form-label">Protocol</label>
<select

              className = "form-input"

              value     = {form.protocol}

              onChange  = {e => update('protocol', e.target.value)}
>
<option value="tcp">TCP (Samsung MDC, LG, etc.)</option>
<option value="http">HTTP (REST API devices)</option>
<option value="https">HTTPS (REST API devices)</option>
<option value="serial">Serial / RS232</option>
</select>
</div>
 
          <div className="form-group">
<label className="form-label">Timeout (seconds)</label>
<input

              className = "form-input"

              type      = "number"

              min       = "1"

              max       = "30"

              value     = {form.timeout}

              onChange  = {e => update('timeout', e.target.value)}

            />
</div>
</div>
 
        <div>
<div className="form-group">
<label className="form-label">Payload Type</label>
<select

              className = "form-input"

              value     = {form.payload_type}

              onChange  = {e => update('payload_type', e.target.value)}
>
<option value="hex">HEX bytes (AA 11 01 00 11)</option>
<option value="ascii">ASCII string (PON\r\n)</option>
</select>
</div>
 
          <div className="form-group">
<label className="form-label">Payload Data</label>
<textarea

              className = "form-input"

              rows      = {4}

              placeholder = "AA 11 01 00 11"

              value     = {form.payload_data}

              onChange  = {e => update('payload_data', e.target.value)}

              style     = {{ resize: 'vertical', lineHeight: 1.8 }}

            />
<div className="form-hint">

              HEX: space-separated bytes like AA 11 01 00 11
</div>
</div>
 
          <div className="form-group">
<label style={{

              display:    'flex',

              alignItems: 'center',

              gap:        8,

              cursor:     'pointer',

            }}>
<input

                type     = "checkbox"

                checked  = {form.expect_response}

                onChange = {e => update('expect_response', e.target.checked)}

              />
<span className="form-label" style={{ marginBottom: 0 }}>

                Expect response from device
</span>
</label>
</div>
</div>
</div>
 
      <button

        className = "btn primary"

        onClick   = {handleTest}

        disabled  = {loading || !form.ip_address}
>

        {loading

          ? <><div className="spinner" style={{ width: 13, height: 13 }} /> Sending...</>

          : '▶ Send Test Command'

        }
</button>
 
      {/* Result */}

      {result && (
<div style={{ marginTop: 16 }}>
<div className={`alert ${result.type}`}>

            {result.type === 'success' ? '✓ Command sent successfully' : '✗ Command failed'}
</div>
<pre style={{

            background:    'var(--bg-base)',

            border:        '1px solid var(--border)',

            borderRadius:  'var(--radius-sm)',

            padding:       14,

            fontFamily:    'var(--font-mono)',

            fontSize:      12,

            color:         'var(--text-secondary)',

            overflow:      'auto',

            maxHeight:     200,

          }}>

            {JSON.stringify(result.data, null, 2)}
</pre>
</div>

      )}
</div>

  );

}
 
// ── Device Card ──────────────────────────────────────────

function DeviceCard({ device }) {

  return (
<div style={{

      background:   'var(--bg-card)',

      border:       `1px solid var(--border)`,

      borderLeft:   `3px solid ${

        device.status === 'online'

          ? 'var(--green)'

          : device.status === 'offline'

            ? 'var(--red)'

            : 'var(--yellow)'

      }`,

      borderRadius: 'var(--radius)',

      padding:      18,

      opacity:      device.status === 'offline' ? 0.7 : 1,

    }}>
 
      {/* Header */}
<div style={{

        display:        'flex',

        justifyContent: 'space-between',

        alignItems:     'flex-start',

        marginBottom:   12,

      }}>
<div>
<div style={{

            fontWeight: 600,

            fontSize:   14,

            color:      'var(--text-primary)',

          }}>

            {device.name}
</div>
<div style={{

            fontFamily: 'var(--font-mono)',

            fontSize:   11,

            color:      'var(--text-secondary)',

            marginTop:  2,

          }}>

            {device.type} · {device.protocol}
</div>
</div>
 
        <span className={`status-badge ${device.status || 'unknown'}`}>
<span className={`status-dot ${device.status || 'unknown'}`} />

          {device.status || 'unknown'}
</span>
</div>
 
      {/* Device Details */}
<div style={{

        fontFamily: 'var(--font-mono)',

        fontSize:   11,

        color:      'var(--text-secondary)',

        lineHeight: 1.8,

      }}>
<div>IP: {device.ip_address}</div>
<div>Port: {device.port}</div>

        {device.location && <div>Location: {device.location}</div>}
</div>
 
      {/* Info Note */}
<div style={{

        marginTop:    10,

        padding:      '6px 10px',

        background:   'var(--bg-base)',

        borderRadius: 'var(--radius-sm)',

        fontFamily:   'var(--font-mono)',

        fontSize:     10,

        color:        'var(--text-muted)',

      }}>

        Commands are sent from the Cloud Dashboard
</div>
 
    </div>

  );

}
 
// ── Main Devices Page ────────────────────────────────────

export default function Devices() {

  const [devices,     setDevices]     = useState([]);

  const [loading,     setLoading]     = useState(true);

  const [lastRefresh, setLastRefresh] = useState(null);
 
  const fetchDevices = useCallback(() => {

    devicesAPI.getDevices()

      .then(res => {

        setDevices(res.data.devices || []);

        setLastRefresh(new Date().toLocaleTimeString());

      })

      .catch(console.error)

      .finally(() => setLoading(false));

  }, []);
 
  useEffect(() => {

    fetchDevices();

    const interval = setInterval(fetchDevices, 15000);

    return () => clearInterval(interval);

  }, [fetchDevices]);
 
  const onlineCount  = devices.filter(d => d.status === 'online').length;

  const offlineCount = devices.filter(d => d.status === 'offline').length;
 
  return (
<div>
 
      {/* ── Page Header ──────────────────────────────── */}
<div className="page-header">
<div>
<div className="page-title">Devices</div>
<div className="page-subtitle">

            {devices.length} devices · {onlineCount} online · {offlineCount} offline

            {lastRefresh && (
<span style={{

                marginLeft: 12,

                fontFamily: 'var(--font-mono)',

                fontSize:   11,

              }}>

                Updated: {lastRefresh}
</span>

            )}
</div>
</div>
<button

          className = "btn"

          onClick   = {fetchDevices}

          disabled  = {loading}
>

          {loading

            ? <><div className="spinner" style={{ width: 12, height: 12 }} /> Loading...</>

            : '↻ Refresh'

          }
</button>
</div>
 
      {/* ── No Devices State ──────────────────────────── */}

      {!loading && devices.length === 0 && (
<div className="alert info" style={{ marginBottom: 20 }}>

          ℹ No devices assigned to this edge yet.

          Devices are assigned from the Cloud Dashboard after

          this edge registers with the cloud.
</div>

      )}
 
      {/* ── Device Cards Grid ─────────────────────────── */}

      {devices.length > 0 && (
<div style={{

          display:               'grid',

          gridTemplateColumns:   'repeat(auto-fill, minmax(280px, 1fr))',

          gap:                   16,

          marginBottom:          24,

        }}>

          {devices.map(device => (
<DeviceCard key={device.id} device={device} />

          ))}
</div>

      )}
 
      {/* ── Test Command Panel ────────────────────────── */}
<TestCommandPanel />
 
    </div>

  );

}
 