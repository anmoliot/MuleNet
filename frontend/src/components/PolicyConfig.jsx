import React, { useState, useEffect } from 'react';
import { Settings, CheckCircle, GitBranch } from 'lucide-react';
import { api, MetricCard } from './Common';

export default function PolicyConfig() {
  const [thresholds, setThresholds] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api('/api/cases/policy/thresholds').then(setThresholds).catch(console.error);
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const result = await api('/api/cases/policy/thresholds', {
        method: 'PUT',
        body: JSON.stringify(thresholds),
      });
      setThresholds(result);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const labels = {
    freeze_threshold: { label: 'Auto-Freeze Threshold', desc: 'Accounts scoring above this are immediately frozen', color: 'var(--accent-red)' },
    escalation_threshold: { label: 'Escalation Threshold', desc: 'Cases above this are auto-escalated to senior investigator', color: 'var(--accent-orange)' },
    soft_hold_threshold: { label: 'Soft-Hold Threshold', desc: 'Transactions held pending manual review', color: 'var(--accent-yellow)' },
    monitor_threshold: { label: 'Step-Up Monitoring', desc: 'Enhanced monitoring is activated', color: 'var(--accent-primary)' },
  };

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header">
          <div className="card-title"><Settings size={16} className="icon" /> Policy & Intervention Configuration</div>
          <button className="btn-analyze" onClick={save} disabled={saving} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {saved ? <><CheckCircle size={14} /> Saved!</> : saving ? 'Saving…' : '💾 Save Thresholds'}
          </button>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '20px' }}>
          Layer 7 — Configure policy thresholds that map ML risk scores to automated interventions.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {Object.entries(labels).map(([key, meta]) => (
            <div key={key} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px', color: meta.color }}>{meta.label}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{meta.desc}</div>
                </div>
                <div style={{ fontSize: '24px', fontWeight: 800, color: meta.color, fontFamily: 'var(--font-mono)' }}>
                  {thresholds[key]?.toFixed(0) ?? '—'}
                </div>
              </div>
              <input
                type="range" min="0" max="100" step="5"
                value={thresholds[key] || 0}
                onChange={e => setThresholds({ ...thresholds, [key]: parseFloat(e.target.value) })}
                style={{ width: '100%', accentColor: meta.color }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-muted)' }}>
                <span>0 (Allow all)</span>
                <span>100 (Block all)</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Fusion weights display */}
      <div className="card">
        <div className="card-header">
          <div className="card-title"><GitBranch size={16} className="icon" /> Layer 6 — Risk Fusion Weights</div>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '16px' }}>
          These weights control how the 4 scoring channels are combined. Configured via ML service environment variables.
        </p>
        <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
          <MetricCard label="Fast Path (XGB)" value="30%" sub="FUSION_W_FAST" accent="metric-accent" />
          <MetricCard label="GNN Deep Path" value="35%" sub="FUSION_W_GNN" accent="metric-up" />
          <MetricCard label="Topology" value="20%" sub="FUSION_W_TOPO" accent="metric-orange" />
          <MetricCard label="External Intel" value="15%" sub="FUSION_W_EXT" accent="metric-down" />
        </div>
      </div>
    </div>
  );
}
