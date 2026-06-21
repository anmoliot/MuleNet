import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Zap, FileText, ChevronRight, Download } from 'lucide-react';
import { api, MetricCard, RiskBadge, StatusBadge, Spinner } from './Common';
import { testIntakeRequest } from '../testData';

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [minRisk, setMinRisk] = useState(0);
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('query', searchQuery);
      if (statusFilter) params.append('status', statusFilter);
      if (severityFilter) params.append('severityLevel', severityFilter);
      if (minRisk > 0) params.append('minRisk', minRisk);

      const [c, s] = await Promise.all([
        api(`/api/cases?${params.toString()}`),
        api('/api/cases/stats/summary'),
      ]);
      setCases(c);
      setStats(s);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter, severityFilter, minRisk]);

  useEffect(() => { loadData(); }, [loadData]);

  const runAnalysis = async () => {
    setLoading(true);
    try {
      const result = await api('/api/intake', {
        method: 'POST',
        body: JSON.stringify(testIntakeRequest),
      });
      await loadData();
      if (result.caseId) navigate(`/cases/${result.caseId}`);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    const token = localStorage.getItem('token');
    fetch(`${API}/api/cases/export/csv`, {
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
      a.download = `cases_export_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    })
    .catch(err => {
      console.error(err);
      alert("Failed to export cases CSV");
    });
  };

  const userRole = localStorage.getItem('role');
  const canExport = ['SUPERVISOR', 'COMPLIANCE_OFFICER', 'FRAUD_ADMIN'].includes(userRole);

  return (
    <div className="main-content">
      {/* Metric Row */}
      <div className="metric-grid">
        <MetricCard label="Active Cases" value={stats.active_cases ?? '—'} sub="Open + Investigating" accent="metric-orange" />
        <MetricCard label="Critical Alerts" value={stats.critical_alerts ?? '—'} sub="Score > 80" accent="metric-down" />
        <MetricCard label="Frozen Accounts" value={stats.frozen_accounts ?? '—'} sub="Freeze executed" accent="metric-accent" />
        <MetricCard label="Avg Risk Score" value={stats.avg_risk_score ?? '—'} sub="Across all cases" accent="metric-up" />
      </div>

      {/* Search & Filters */}
      <div className="card" style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center', background: 'rgba(255,255,255,0.01)', padding: '15px' }}>
        <div style={{ flex: 1, minWidth: '200px', display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '6px 12px' }}>
          <Search size={14} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search Case ID / Complaint ID..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ background: 'none', border: 'none', outline: 'none', color: 'var(--text-primary)', fontSize: '13px', width: '100%' }}
          />
        </div>

        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '8px 12px', color: 'var(--text-primary)', fontSize: '13px', cursor: 'pointer' }}
        >
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="INVESTIGATING">Investigating</option>
          <option value="ESCALATED">Escalated</option>
          <option value="FROZEN">Frozen</option>
          <option value="CLOSED">Closed</option>
          <option value="DISMISSED">Dismissed</option>
        </select>

        <select
          value={severityFilter}
          onChange={e => setSeverityFilter(e.target.value)}
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '8px 12px', color: 'var(--text-primary)', fontSize: '13px', cursor: 'pointer' }}
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: '200px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Min Risk: {minRisk}%</span>
          <input
            type="range" min="0" max="100" step="5"
            value={minRisk}
            onChange={e => setMinRisk(parseInt(e.target.value))}
            style={{ flex: 1, accentColor: 'var(--accent-primary)', height: '4px' }}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="card">
        <div className="card-header">
          <div className="card-title"><Zap className="icon" size={16} /> Quick Analysis</div>
          <button className="btn-analyze" onClick={runAnalysis} disabled={loading}>
            {loading ? 'Analyzing…' : '⚡ Run Intake Analysis'}
          </button>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
          Submit the test complaint through the full 11-layer pipeline: Data Ingestion → Trust Fabric → Risk Mesh → Knowledge Graph → XGBoost → GNN → Risk Fusion → Policy Engine → Recovery Intelligence
        </p>
        {loading && <Spinner />}
      </div>

      {/* Case Queue */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="card-title"><FileText className="icon" size={16} /> Case Queue</div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span className="stat-chip">{cases.length} total</span>
            {canExport && (
              <button 
                onClick={handleExportCSV}
                className="btn-analyze"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '12px' }}
              >
                <Download size={14} /> Export CSV
              </button>
            )}
          </div>
        </div>
        {cases.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '20px 0', textAlign: 'center' }}>
            No cases yet. Run an analysis to create your first case.
          </p>
        ) : (
          <div className="ranking-list">
            {cases.map((c, i) => (
              <div key={c.caseId} className="rank-item" onClick={() => navigate(`/cases/${c.caseId}`)}>
                <span className="rank-num">#{i + 1}</span>
                <span className="rank-acct">{c.caseId}</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{c.complaintId}</span>
                <StatusBadge status={c.status} />
                <RiskBadge level={c.severityLevel === 'CRITICAL' || c.severityLevel === 'HIGH' ? 'HIGH' : c.severityLevel === 'MEDIUM' ? 'MEDIUM' : 'LOW'} />
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent-orange)', minWidth: '50px', textAlign: 'right' }}>
                  {c.riskScore?.toFixed(1)}
                </span>
                <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
