import React, { useState, useEffect } from 'react';
import { ShieldAlert, Download } from 'lucide-react';
import { api, Spinner, API } from './Common';

export default function AuditLedger() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api('/api/audit-logs')
      .then(setLogs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleExportCSV = () => {
    const token = localStorage.getItem('token');
    fetch(`${API}/api/audit-logs/export/csv`, {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })
    .then(res => {
      if (!res.ok) throw new Error("Failed to export");
      return res.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_ledger_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    })
    .catch(err => {
      console.error(err);
      alert("Failed to export audit ledger CSV");
    });
  };

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="card-title">
            <ShieldAlert size={16} className="icon" /> Immutable Security Audit Ledger
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span className="stat-chip">{logs.length} events logged</span>
            <button 
              onClick={handleExportCSV}
              className="btn-analyze"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
            >
              <Download size={14} /> Export CSV
            </button>
          </div>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '16px' }}>
          Layer 10 Governance — Cryptographically-linked audit trail tracking all investigator overrides, policy updates, and critical system events.
        </p>

        {loading ? (
          <Spinner />
        ) : logs.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px 0' }}>
            No audit logs found. Ensure you are logged in as Supervisor or Compliance Officer.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px' }}>Timestamp</th>
                  <th style={{ padding: '10px' }}>Actor</th>
                  <th style={{ padding: '10px' }}>Role</th>
                  <th style={{ padding: '10px' }}>Action</th>
                  <th style={{ padding: '10px' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {log.timestamp?.replace('T', ' ').slice(0, 19)}
                    </td>
                    <td style={{ padding: '10px', fontWeight: 600, color: 'var(--accent-primary)' }}>{log.actor}</td>
                    <td style={{ padding: '10px' }}>
                      <span style={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '4px',
                        padding: '2px 6px',
                        fontSize: '10px',
                        color: log.role === 'FRAUD_ADMIN' ? 'var(--accent-red)' : log.role === 'SUPERVISOR' ? 'var(--accent-orange)' : 'var(--text-secondary)'
                      }}>
                        {log.role}
                      </span>
                    </td>
                    <td style={{ padding: '10px', fontWeight: 600 }}>{log.action}</td>
                    <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>{log.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
