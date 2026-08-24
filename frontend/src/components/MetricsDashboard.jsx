import React, { useEffect, useState } from 'react';
import { BarChart3, Gauge, RefreshCw } from 'lucide-react';
import { ML_API, Spinner } from './Common';

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [threshold, setThreshold] = useState(0.8);

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${ML_API}/api/v1/metrics?threshold=${threshold}&n_test=70`);
      const data = await res.json();
      setMetrics(data.metrics);
    } catch (error) {
      console.error(error);
      alert('Unable to load held-out metrics from ML service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  const matrix = metrics?.confusion_matrix || {};

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header">
          <div className="card-title"><BarChart3 size={16} className="icon" /> Metrics Dashboard</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="stat-chip">Threshold {(threshold * 100).toFixed(0)}%</span>
            <input style={{ width: 150 }} type="range" min="0.65" max="0.95" step="0.05" value={threshold} onChange={e => setThreshold(Number(e.target.value))} />
            <button className="btn-analyze" onClick={loadMetrics} disabled={loading}><RefreshCw size={14} /> Refresh</button>
          </div>
        </div>
        {loading && <Spinner />}
        {metrics && (
          <>
            <div className="metric-grid">
              <GaugeCard label="Precision" value={metrics.precision} color="var(--accent-green)" />
              <GaugeCard label="Recall" value={metrics.recall} color="var(--accent-primary)" />
              <GaugeCard label="FPR" value={metrics.false_positive_rate} color="var(--accent-red)" invert />
              <div className="metric-card">
                <div className="metric-label">False-Positive Cost</div>
                <div className="metric-value metric-down">INR {metrics.false_positive_cost_inr.toLocaleString()}</div>
                <div className="metric-sub">INR {metrics.cost_per_false_positive_inr.toLocaleString()} per FP</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, .55fr) 1fr', gap: 14, marginTop: 14 }}>
              <div className="card" style={{ margin: 0 }}>
                <div className="card-header">
                  <div className="card-title"><Gauge size={16} className="icon" /> Confusion Matrix</div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <Cell label="True Positive" value={matrix.tp} color="var(--accent-green)" />
                  <Cell label="False Positive" value={matrix.fp} color="var(--accent-red)" />
                  <Cell label="False Negative" value={matrix.fn} color="var(--accent-orange)" />
                  <Cell label="True Negative" value={matrix.tn} color="var(--accent-cyan)" />
                </div>
              </div>
              <div className="card" style={{ margin: 0 }}>
                <div className="card-header">
                  <div className="card-title"><BarChart3 size={16} className="icon" /> Evaluation Summary</div>
                  <span className="stat-chip">{metrics.run_id}</span>
                </div>
                <div className="explain-block">
                  <span className="tag tag-tech">Held-out synthetic Razorpay graph</span>
                  {metrics.graph_summary.total_nodes} nodes, {metrics.graph_summary.total_edges} payout edges, {metrics.detection_summary.flagged_accounts} flagged accounts, and {metrics.clusters_detected} clusters. F1 score is {metrics.f1}.
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function GaugeCard({ label, value, color, invert }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color }}>{pct}%</div>
      <div style={{ height: 8, background: 'var(--bg-elevated)', borderRadius: 4, overflow: 'hidden', marginTop: 10 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color }} />
      </div>
      <div className="metric-sub">{invert ? 'lower is better' : 'higher is better'}</div>
    </div>
  );
}

function Cell({ label, value, color }) {
  return (
    <div style={{ border: `1px solid ${color}`, background: 'var(--bg-elevated)', borderRadius: 8, padding: 14 }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color }}>{value ?? 0}</div>
    </div>
  );
}
