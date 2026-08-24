import React, { useEffect, useState } from 'react';
import { AlertTriangle, Bot, Download, GitBranch, RefreshCw } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ML_API, RiskBadge, Spinner } from './Common';

function mlFetch(path, opts = {}) {
  const token = localStorage.getItem('token');
  return fetch(`${ML_API}${path}`, {
    ...opts,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opts.headers,
    },
  });
}

const bucketLabels = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  minimal: 'Minimal',
};

const bucketColors = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#06b6d4',
  minimal: '#22c55e',
};

export default function MerchantRiskOverview() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [threshold, setThreshold] = useState(0.8);
  const [nAccounts, setNAccounts] = useState(60);

  const runDetection = async () => {
    setLoading(true);
    try {
      const res = await mlFetch(`/api/v1/detect?n_accounts=${nAccounts}&threshold=${threshold}`);
      if (!res.ok) throw new Error(`Detect ${res.status}`);
      const data = await res.json();
      setReport(data.report);
      localStorage.setItem('lastMerchantRunId', data.report.run_id);
    } catch (error) {
      console.error(error);
      alert('Unable to reach ML service on port 8000.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runDetection();
  }, []);

  const scores = Object.values(report?.scores || {});
  const highRisk = scores.filter(item => item.flagged).slice(0, 8);
  const distribution = Object.entries(report?.score_distribution || {}).map(([key, value]) => ({
    name: bucketLabels[key] || key,
    key,
    count: value,
  }));

  const exportJson = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${report.run_id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header">
          <div className="card-title"><Bot size={16} className="icon" /> Merchant Risk Overview</div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <label className="stat-chip">Threshold {(threshold * 100).toFixed(0)}%</label>
            <input style={{ width: 140 }} type="range" min="0.65" max="0.95" step="0.05" value={threshold} onChange={e => setThreshold(Number(e.target.value))} />
            <input className="form-input" style={{ width: 92 }} type="number" min="20" max="120" value={nAccounts} onChange={e => setNAccounts(Number(e.target.value))} />
            <button className="btn-analyze" onClick={runDetection} disabled={loading}>
              <RefreshCw size={14} /> {loading ? 'Running...' : 'Run Detect'}
            </button>
            <button className="btn-analyze" onClick={exportJson} disabled={!report} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
              <Download size={14} /> JSON
            </button>
          </div>
        </div>
        {loading && <Spinner />}
        {report && (
          <>
            <div className="metric-grid">
              <Metric label="Scored Accounts" value={report.detection_summary.total_accounts_scored} sub={`${report.graph_summary.total_edges} transactions`} />
              <Metric label="Flagged" value={report.detection_summary.flagged_accounts} sub={`threshold ${Math.round(report.config.threshold * 100)}%`} accent="metric-orange" />
              <Metric label="Clusters" value={report.detection_summary.clusters_detected} sub="mule-ring indicators" accent="metric-accent" />
              <Metric label="FP Cost" value={`INR ${report.false_positive_cost_analysis.false_positive_cost_inr.toLocaleString()}`} sub="held-label estimate" accent="metric-down" />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(320px, 0.8fr)', gap: 14, marginTop: 14 }}>
              <div className="card" style={{ margin: 0 }}>
                <div className="card-header">
                  <div className="card-title"><AlertTriangle size={16} className="icon" /> Risk Score Distribution</div>
                  <span className="stat-chip">{report.run_id}</span>
                </div>
                <div style={{ height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={distribution}>
                      <CartesianGrid stroke="rgba(91, 141, 239, 0.10)" vertical={false} />
                      <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                      <YAxis stroke="#94a3b8" fontSize={11} />
                      <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(91,141,239,.22)', color: '#f1f5f9' }} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {distribution.map(entry => <Cell key={entry.key} fill={bucketColors[entry.key]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="card" style={{ margin: 0 }}>
                <div className="card-header">
                  <div className="card-title"><GitBranch size={16} className="icon" /> High-Risk Alerts</div>
                  <span className="stat-chip">{highRisk.length} shown</span>
                </div>
                <div className="ranking-list">
                  {highRisk.map((item, index) => (
                    <div className="rank-item" key={item.account_id} style={{ cursor: 'default' }}>
                      <span className="rank-num">#{index + 1}</span>
                      <span className="rank-acct">{item.account_id}</span>
                      <RiskBadge level={item.risk_level === 'CRITICAL' ? 'HIGH' : item.risk_level} />
                      <span style={{ fontWeight: 800, color: 'var(--accent-orange)' }}>{item.composite_score}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="card" style={{ margin: 0 }}>
              <div className="card-header">
                <div className="card-title"><GitBranch size={16} className="icon" /> Mule Ring Cluster Indicators</div>
                <span className="stat-chip">{report.clusters.length} clusters</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10 }}>
                {report.clusters.map(cluster => (
                  <div className="explain-block" key={cluster.cluster_id}>
                    <span className="tag tag-ops">{cluster.cluster_id} | {cluster.cluster_type}</span>
                    <strong>{cluster.size} accounts</strong> with average risk {cluster.avg_risk_score}. Flow: INR {cluster.total_flow.toLocaleString()}.
                    <div style={{ marginTop: 8, color: 'var(--text-muted)' }}>{cluster.accounts.slice(0, 6).join(', ')}</div>
                  </div>
                ))}
                {report.clusters.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No connected mule clusters detected at this threshold.</p>}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, sub, accent }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${accent || ''}`}>{value}</div>
      <div className="metric-sub">{sub}</div>
    </div>
  );
}
