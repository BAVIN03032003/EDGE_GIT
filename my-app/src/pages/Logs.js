import React, { useState, useEffect, useRef, useCallback } from 'react';

import { logsAPI } from '../services/api';
 
const LEVELS      = ['ALL', 'INFO', 'WARNING', 'ERROR', 'DEBUG'];

const LINE_OPTIONS = [50, 100, 200, 500];
 
const LEVEL_COLORS = {

  INFO:    'var(--accent)',

  WARNING: 'var(--yellow)',

  ERROR:   'var(--red)',

  DEBUG:   'var(--text-muted)',

};
 
export default function Logs() {

  const [logs,        setLogs]        = useState([]);

  const [loading,     setLoading]     = useState(true);

  const [level,       setLevel]       = useState('ALL');

  const [lines,       setLines]       = useState(100);

  const [autoRefresh, setAutoRefresh] = useState(true);

  const [lastFetch,   setLastFetch]   = useState(null);

  const logRef = useRef(null);
 
  const fetchLogs = useCallback(() => {

    logsAPI.getLogs(lines, level)

      .then(res => {

        setLogs(res.data.logs || []);

        setLastFetch(new Date().toLocaleTimeString());

      })

      .catch(console.error)

      .finally(() => setLoading(false));

  }, [lines, level]);
 
  // Auto refresh every 5 seconds

  useEffect(() => {

    fetchLogs();

    if (!autoRefresh) return;

    const interval = setInterval(fetchLogs, 5000);

    return () => clearInterval(interval);

  }, [fetchLogs, autoRefresh]);
 
  const errorCount   = logs.filter(l => l.level === 'ERROR').length;

  const warningCount = logs.filter(l => l.level === 'WARNING').length;
 
  return (
<div>
 
      {/* ── Page Header ──────────────────────────────── */}
<div className="page-header">
<div>
<div className="page-title">Logs</div>
<div className="page-subtitle">

            {logs.length} entries

            {errorCount > 0 && (
<span style={{

                marginLeft:  10,

                color:       'var(--red)',

                fontFamily:  'var(--font-mono)',

                fontSize:    11,

              }}>

                {errorCount} errors
</span>

            )}

            {warningCount > 0 && (
<span style={{

                marginLeft:  10,

                color:       'var(--yellow)',

                fontFamily:  'var(--font-mono)',

                fontSize:    11,

              }}>

                {warningCount} warnings
</span>

            )}

            {lastFetch && (
<span style={{

                marginLeft: 10,

                fontFamily: 'var(--font-mono)',

                fontSize:   11,

              }}>

                · Updated: {lastFetch}
</span>

            )}
</div>
</div>
 
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>

          {/* Auto Refresh Toggle */}
<label style={{

            display:    'flex',

            alignItems: 'center',

            gap:        6,

            cursor:     'pointer',

            fontFamily: 'var(--font-mono)',

            fontSize:   12,

            color:      'var(--text-secondary)',

          }}>
<input

              type     = "checkbox"

              checked  = {autoRefresh}

              onChange = {e => setAutoRefresh(e.target.checked)}

            />

            Auto refresh
</label>
 
          <button className="btn sm" onClick={fetchLogs}>

            ↻ Refresh
</button>
</div>
</div>
 
      {/* ── Filters Bar ───────────────────────────────── */}
<div className="card" style={{ padding: '12px 16px', marginBottom: 16 }}>
<div style={{

          display:    'flex',

          gap:        12,

          alignItems: 'center',

          flexWrap:   'wrap',

        }}>
 
          {/* Level Filter Buttons */}
<div style={{ display: 'flex', gap: 4 }}>

            {LEVELS.map(l => (
<button

                key       = {l}

                className = {`btn sm ${level === l ? 'primary' : ''}`}

                onClick   = {() => setLevel(l)}

                style     = {level !== l && l !== 'ALL' ? {

                  color:       LEVEL_COLORS[l],

                  borderColor: `${LEVEL_COLORS[l]}44`,

                } : {}}
>

                {l}
</button>

            ))}
</div>
 
          {/* Lines Selector */}
<div style={{

            display:    'flex',

            alignItems: 'center',

            gap:        8,

            marginLeft: 'auto',

          }}>
<span style={{

              fontFamily:   'var(--font-mono)',

              fontSize:     11,

              color:        'var(--text-muted)',

              textTransform: 'uppercase',

              letterSpacing: 0.5,

            }}>

              Show
</span>
<select

              value    = {lines}

              onChange = {e => setLines(Number(e.target.value))}

              style    = {{

                background:  'var(--bg-base)',

                border:      '1px solid var(--border)',

                borderRadius: 4,

                color:       'var(--text-primary)',

                fontFamily:  'var(--font-mono)',

                fontSize:    12,

                padding:     '4px 8px',

              }}
>

              {LINE_OPTIONS.map(n => (
<option key={n} value={n}>{n} lines</option>

              ))}
</select>
</div>
 
        </div>
</div>
 
      {/* ── Log Display ───────────────────────────────── */}
<div className="log-container" ref={logRef}>
 
        {loading && (
<div className="loading">
<div className="spinner" /> Loading logs...
</div>

        )}
 
        {!loading && logs.length === 0 && (
<div style={{

            textAlign:  'center',

            padding:    '30px 0',

            color:      'var(--text-muted)',

            fontFamily: 'var(--font-mono)',

            fontSize:   12,

          }}>

            No log entries found.

            {level !== 'ALL' && ` Try switching filter to ALL.`}
</div>

        )}
 
        {logs.map((log, i) => (
<div key={i} className="log-entry">
<span className="log-time">{log.timestamp}</span>
<span

              className = "log-level"

              style     = {{ color: LEVEL_COLORS[log.level] || 'inherit' }}
>

              {log.level}
</span>
<span className="log-message">{log.message}</span>
</div>

        ))}
 
      </div>
 
    </div>

  );

}
 