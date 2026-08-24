import React, { useEffect, useState } from 'react';
import { Download, FileText, Search } from 'lucide-react';
import { ML_API, Spinner } from './Common';

export default function AuditTrailViewer() {
  const [runId, setRunId] = useState(localStorage.getItem('lastMerchantRunId') || '');
  const [audit, setAudit] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadAudit = async () => {
    if (!runId) return;
    setLoading(true);
    try {
      const res = await fetch(`${ML_API}/api/v1/audit/${runId}`);
      if (!res.ok) throw new Error(`Audit ${res.status}`);
      setAudit(await res.json());
    } catch (error) {
      console.error(error);
      alert('Run an overview detection first, or enter an existing run id.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (runId) loadAudit();
  }, []);

  const exportCsv = () => {
    if (!audit) return;
    const rows = [['timestamp', 'event', 'description'], ...audit.audit_log.map(row => [row.timestamp, row.event, row.description])];
    const csv = rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    download(new Blob([csv], { type: 'text/csv' }), `${audit.run_id}-audit.csv`);
  };

  const exportJson = () => {
    if (!audit) return;
    download(new Blob([JSON.stringify(audit, null, 2)], { type: 'application/json' }), `${audit.run_id}-audit.json`);
  };

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header">
          <div className="card-title"><FileText size={16} className="icon" /> Exportable Audit Trail</div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '6px 10px' }}>
              <Search size={14} style={{ color: 'var(--text-muted)' }} />
              <input value={runId} onChange={e => setRunId(e.target.value)} placeholder="run id" style={{ background: 'transparent', border: 0, outline: 0, color: 'var(--text-primary)', minWidth: 260 }} />
            </div>
            <button className="btn-analyze" onClick={loadAudit}>Load</button>
            <button className="btn-analyze" onClick={exportCsv} disabled={!audit} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}><Download size={14} /> CSV</button>
            <button className="btn-analyze" onClick={exportJson} disabled={!audit} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}><Download size={14} /> JSON</button>
          </div>
        </div>
        {loading && <Spinner />}
        {audit && (
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, .9fr) minmax(320px, 1.1fr)', gap: 14 }}>
            <div className="card" style={{ margin: 0 }}>
              <div className="card-header">
                <div className="card-title">Audit Log</div>
                <span className="stat-chip">{audit.audit_log.length} events</span>
              </div>
              <div className="ranking-list">
                {audit.audit_log.map((row, index) => (
                  <div className="rank-item" key={`${row.event}-${index}`} style={{ cursor: 'default', alignItems: 'flex-start' }}>
                    <span className="rank-num">#{index + 1}</span>
                    <div style={{ flex: 1 }}>
                      <div className="rank-acct">{row.event}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>{row.timestamp}</div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{row.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="card" style={{ margin: 0 }}>
              <div className="card-header">
                <div className="card-title">Per-Account Explanation Cards</div>
                <span className="stat-chip">{Object.keys(audit.explanations || {}).length} accounts</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {Object.entries(audit.explanations || {}).map(([accountId, detail]) => (
                  <div className="explain-block" key={accountId}>
                    <span className="tag tag-ops">{accountId}</span>
                    <strong>Drivers:</strong> {(detail.top_5_risk_drivers || []).join(', ') || 'No drivers available'}
                    <div style={{ marginTop: 6 }}>{detail.explainability?.operational || detail.reason_codes?.join(', ') || detail.message || 'Explanation generated.'}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
