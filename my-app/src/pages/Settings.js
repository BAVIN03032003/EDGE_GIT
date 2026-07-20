import React, { useState, useEffect } from 'react';
import { configAPI } from '../services/api';

export default function Settings() {
  const [config, setConfig] = useState({
    CLOUD_URL: '',
    API_KEY: '',
    EDGE_NAME: '',
    LOCATION: '',
    WEB_UI_PORT: 8080,
    is_manual_update: 0,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeySet, setApiKeySet] = useState(false);

  // Load current config on mount
  useEffect(() => {
    configAPI.getConfig()
      .then(res => {
        setConfig(res.data.config || res.data);
        setApiKeySet(res.data.api_key_set || (res.data.config && res.data.config.api_key !== null));
      })
      .catch(() => setMessage({
        type: 'error',
        text: 'Failed to load config. Is the backend running?'
      }))
      .finally(() => setLoading(false));
  }, []);

  const update = (key, value) =>
    setConfig(prev => ({ ...prev, [key]: value }));

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    // Don't send masked API key back
    const payload = { ...config };
    if (payload.API_KEY === '***' || payload.api_key?.includes('***')) {
      delete payload.API_KEY;
      delete payload.api_key;
    }

    try {
      await configAPI.saveConfig(payload);
      setMessage({
        type: 'success',
        text: 'Configuration saved. Cloud connection will restart automatically. Some settings (like Web UI port) still require a full restart.',
      });
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to save configuration.',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" /> Loading configuration...
      </div>
    );
  }

  return (
    <div>
      {/* ── Page Header ──────────────────────────────── */}
      <div className="page-header">
        <div>
          <div className="page-title">Settings</div>
          <div className="page-subtitle">
            Configure cloud connection and edge identity
          </div>
        </div>
      </div>

      {/* ── Save Message ──────────────────────────────── */}
      {message && (
        <div className={`alert ${message.type}`}>
          {message.type === 'success' ? '✓' : '✗'} {message.text}
        </div>
      )}

      <form onSubmit={handleSave}>
        <div className="grid-2">
          {/* ── Cloud Connection ────────────────────── */}
          <div className="card">
            <div className="card-title">Cloud Connection</div>

            <div className="form-group">
              <label className="form-label">Cloud URL *</label>
              <input
                className="form-input"
                type="url"
                placeholder="https://your-cloud-server.com"
                value={config.CLOUD_URL || config.cloud_url || ''}
                onChange={e => update('CLOUD_URL', e.target.value)}
                required
              />
              <div className="form-hint">
                The URL of your cloud RMM platform
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                API Key *
                {apiKeySet && (
                  <span style={{
                    marginLeft: 8,
                    color: 'var(--green)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 10,
                  }}>
                    ✓ KEY IS SET
                  </span>
                )}
              </label>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  className="form-input"
                  type={showApiKey ? 'text' : 'password'}
                  placeholder={apiKeySet
                    ? 'Leave blank to keep existing key'
                    : 'sk_your_api_key_from_cloud_dashboard'
                  }
                  value={
                    (config.API_KEY || config.api_key || '').includes('***') ? '' : (config.API_KEY || config.api_key || '')
                  }
                  onChange={e => update('API_KEY', e.target.value)}
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  className="btn sm"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? 'Hide' : 'Show'}
                </button>
              </div>
              <div className="form-hint">
                Generated from the Cloud Dashboard when you create this edge.
                Stored as SHA-256 hash in cloud — never exposed.
              </div>
            </div>
          </div>

          {/* ── Edge Identity ────────────────────────── */}
          <div className="card">
            <div className="card-title">Edge Identity</div>

            <div className="form-group">
              <label className="form-label">Edge Name *</label>
              <input
                className="form-input"
                type="text"
                placeholder="Conference-Room-A"
                value={config.EDGE_NAME || config.edge_name || ''}
                onChange={e => update('EDGE_NAME', e.target.value)}
                required
              />
              <div className="form-hint">
                Friendly name shown in the cloud dashboard
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Location</label>
              <input
                className="form-input"
                type="text"
                placeholder="Building A, Floor 2, Room 101"
                value={config.LOCATION || config.location || ''}
                onChange={e => update('LOCATION', e.target.value)}
              />
              <div className="form-hint">
                Physical location of this edge collector PC
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Web UI Port</label>
              <input
                className="form-input"
                type="number"
                placeholder="5001"
                value={config.WEB_UI_PORT || config.web_ui_port || 5001}
                onChange={e => update('WEB_UI_PORT', Number(e.target.value))}
              />
              <div className="form-hint">
                Port for this local web UI (default: 5001). Requires restart.
              </div>
            </div>
          </div>

          {/* ── Update Preferences ───────────────────── */}
          <div className="card">
            <div className="card-title">Update Preferences</div>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.is_manual_update === 0 || config.IS_MANUAL_UPDATE === 0}
                  onChange={e => {
                    const val = e.target.checked ? 0 : 1;
                    update('is_manual_update', val);
                    update('IS_MANUAL_UPDATE', val);
                  }}
                  style={{ width: 18, height: 18 }}
                />
                <span style={{ fontWeight: 600 }}>Enable Automatic Updates</span>
              </label>
              <div className="form-hint" style={{ marginLeft: 28 }}>
                {(config.is_manual_update === 0 || config.IS_MANUAL_UPDATE === 0)
                  ? "Updates will be downloaded and applied automatically via Watchtower."
                  : "Automatic updates are disabled. You must manually trigger updates."
                }
              </div>
            </div>
          </div>
        </div>

        {/* ── How It Works Info ─────────────────────── */}
        <div className="card">
          <div className="card-title">How API Key Authentication Works</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 12,
          }}>
            {[
              {
                step: '1',
                title: 'Generate on Cloud',
                desc: 'Go to Cloud Dashboard → Edges → Create Edge → Copy the API Key shown once.',
              },
              {
                step: '2',
                title: 'Paste Here',
                desc: 'Paste the API Key into the field above and click Save Configuration.',
              },
              {
                step: '3',
                title: 'Edge Connects',
                desc: 'Edge sends API Key in WebSocket header to cloud on startup.',
              },
              {
                step: '4',
                title: 'Cloud Verifies',
                desc: 'Cloud hashes the key and compares with stored SHA-256 hash in database.',
              },
            ].map(item => (
              <div key={item.step} style={{
                padding: 12,
                background: 'var(--bg-base)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 6,
                }}>
                  <div style={{
                    width: 22,
                    height: 22,
                    background: 'var(--accent)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    fontWeight: 600,
                    color: '#0d1117',
                    flexShrink: 0,
                  }}>
                    {item.step}
                  </div>
                  <div style={{
                    fontWeight: 600,
                    fontSize: 13,
                    color: 'var(--text-primary)',
                  }}>
                    {item.title}
                  </div>
                </div>
                <div style={{
                  fontSize: 12,
                  color: 'var(--text-secondary)',
                  lineHeight: 1.5,
                }}>
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Save Button ───────────────────────────── */}
        <button
          type="submit"
          className="btn primary"
          disabled={saving}
        >
          {saving
            ? <><div className="spinner" style={{ width: 13, height: 13 }} /> Saving...</>
            : '✓ Save Configuration'
          }
        </button>

        <span style={{
          marginLeft: 12,
          fontSize: 12,
          color: 'var(--text-muted)',
        }}>
          Cloud connection will restart automatically after saving. Some settings (like Web UI port) still require a full restart.
        </span>
      </form>
    </div>
  );
}
