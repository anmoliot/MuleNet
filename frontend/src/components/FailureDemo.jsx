import React, { useState } from 'react';
import { AlertCircle, RefreshCw, ShieldCheck } from 'lucide-react';
import { ML_API, Spinner } from './Common';

export default function FailureDemo() {
  const [enabled, setEnabled] = useState(true);
  const [count, setCount] = useState(5);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const runDemo = async () => {
    if (!enabled) return;
    setLoading(true);
    try {
      const res = await fetch(`${ML_API}/api/v1/failure-demo?n_accounts=${count}`, { method: 'POST' });
      const data = await res.json();
      setReport(data.report);
      localStorage.setItem('lastMerchantRunId', data.report.run_id);
    } catch (error) {
      console.error(error);
      alert('Unable to run failure demo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header">
          <div className="card-title"><AlertCircle size={16} className="icon" /> Cold-Start Failure Demo</div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label className="stat-chip" style={{ cursor: 'pointer' }}>
              <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} style={{ marginRight: 6 }} />
              cold-start scenario
            </label>
            <input className="form-input" style={{ width: 80 }} type="number" min="1" max="12" value={count} onChange={e => setCount(Number(e.target.value))} />
            <button className="btn-analyze" onClick={runDemo} disabled={!enabled || loading}><RefreshCw size={14} /> Run Demo</button>
          </div>
        </div>
        {loading && <Spinner />}
        {report && (
          <>
            <div className="metric-grid">
              <div className="metric-card">
                <div className="metric-label">Cold-Start Accounts</div>
                <div className="metric-value metric-orange">{report.cold_start_accounts.length}</div>
                <div className="metric-sub">zero graph history</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Handled Gracefully</div>
                <div className="metric-value metric-up">{report.graceful_failures.length}</div>
                <div className="metric-sub">fallbacks applied</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Action Gate</div>
                <div className="metric-value metric-accent">Monitor</div>
                <div className="metric-sub">no automatic freeze</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Confidence</div>
                <div className="metric-value metric-down">Low</div>
                <div className="metric-sub">human review required</div>
              </div>
            </div>

            <div className="card" style={{ margin: 0 }}>
              <div className="card-header">
                <div className="card-title"><ShieldCheck size={16} className="icon" /> Graceful Degradation Results</div>
                <span className="stat-chip">{report.run_id}</span>
              </div>
              <div className="ranking-list">
                {report.graceful_failures.map(item => (
                  <div className="rank-item" key={item.account_id} style={{ cursor: 'default' }}>
                    <span className="rank-acct">{item.account_id}</span>
                    <span className="stat-chip">{item.issue}</span>
                    <span className="stat-chip">device score {(item.fallback_score * 100).toFixed(0)}%</span>
                    <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{item.action}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
