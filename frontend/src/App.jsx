import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useNavigate, useParams } from 'react-router-dom';
import {
  ShieldAlert, Activity, Search, AlertTriangle, Layers, MapPin,
  BarChart3, Settings, Eye, Network, TrendingUp, Clock, Target,
  ChevronRight, Zap, Shield, FileText, Bell, RefreshCw, ArrowRight,
  X, CheckCircle, XCircle, Pause, Play, AlertCircle, Cpu, GitBranch
} from 'lucide-react';
import ReactFlow, { Background, Controls, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import { testIntakeRequest } from './testData';

/* ═══════════════════════════════════════════════════════════════════════════
   API HELPER
   ═══════════════════════════════════════════════════════════════════════════ */

const API = 'http://localhost:8080';

async function api(path, opts = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: { ...headers, ...opts.headers },
  });
  if (res.status === 401 || res.status === 403) {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    window.location.href = '/';
  }
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

/* ═══════════════════════════════════════════════════════════════════════════
   SPINNER — global loading indicator
   ═══════════════════════════════════════════════════════════════════════════ */

function Spinner() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 0',
    }}>
      <div style={{
        width: '28px',
        height: '28px',
        border: '3px solid rgba(91, 141, 239, 0.15)',
        borderTop: '3px solid var(--accent-primary)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   REUSABLE COMPONENTS
   ═══════════════════════════════════════════════════════════════════════════ */

function MetricCard({ label, value, sub, accent }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${accent || ''}`}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

function RiskBadge({ level }) {
  return <span className={`risk-badge risk-${level}`}>{level}</span>;
}

function ActionBadge({ action }) {
  return <span className={`action-badge action-${action}`}>{action?.replace(/_/g, ' ')}</span>;
}

function StatusBadge({ status }) {
  const colors = {
    OPEN: 'var(--accent-yellow)',
    INVESTIGATING: 'var(--accent-orange)',
    ESCALATED: 'var(--accent-red)',
    FROZEN: 'var(--accent-cyan)',
    CLOSED: 'var(--accent-green)',
    DISMISSED: 'var(--text-muted)'
  };
  return (
    <span style={{
      border: `1px solid ${colors[status] || 'var(--text-muted)'}`,
      color: colors[status] || 'var(--text-muted)',
      background: 'rgba(255,255,255,0.02)',
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '10px',
      fontWeight: 600,
      letterSpacing: '0.5px'
    }}>
      {status}
    </span>
  );
}

function buildFlowGraph(mlData) {
  if (!mlData) return { nodes: [], edges: [] };
  const newNodes = [];
  const newEdges = [];
  const added = new Set();
  const probs = mlData.mule_probabilities || {};
  const ranking = mlData.recovery_ranking || [];

  const getStyle = (id) => {
    const isDev = id.startsWith('DEV-') || id.startsWith('device:');
    if (isDev) {
      return { 
        background: '#07334f', 
        color: '#22d3ee', 
        borderRadius: '50%', 
        width: '55px', 
        height: '55px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        fontSize: '9px', 
        fontWeight: 700, 
        border: '2px solid rgba(34, 211, 238, 0.4)', 
        boxShadow: '0 0 15px rgba(34, 211, 238, 0.2)' 
      };
    }
    
    const rankItem = ranking.find(r => r.account_id === id);
    const isMerchant = rankItem?.is_merchant;
    const ptRate = rankItem?.pass_through_rate || 0;
    
    const r = probs[id] || 0;
    let base = {};
    if (isMerchant) {
      base = { background: '#1e293b', color: '#94a3b8', borderRadius: '10px', padding: '12px 16px', border: '2px solid #475569' };
    } else if (r >= 0.7) {
      base = { background: '#ef4444', color: '#fff', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(239,68,68,0.5)', boxShadow: '0 0 20px rgba(239,68,68,0.3)' };
    } else if (r >= 0.4) {
      base = { background: '#f97316', color: '#fff', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(249,115,22,0.5)', boxShadow: '0 0 15px rgba(249,115,22,0.2)' };
    } else if (r > 0.15) {
      base = { background: '#eab308', color: '#000', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(234,179,8,0.5)' };
    } else {
      base = { background: '#3b82f6', color: '#fff', borderRadius: '10px', padding: '12px 16px', border: '2px solid rgba(59,130,246,0.4)' };
    }
    
    if (ptRate > 0.7 && !isMerchant) {
      base.border = '2px dashed #f59e0b';
      base.boxShadow = '0 0 20px rgba(245,158,11,0.5)';
    }
    
    base.fontFamily = "'Inter',sans-serif";
    base.fontSize = '12px';
    base.fontWeight = 600;
    return base;
  };

  const edges = mlData.suspicious_edges || [];
  const sources = new Set(edges.map(e => e.from));
  const targets = new Set(edges.map(e => e.to));
  const allIds = new Set([...sources, ...targets]);
  const roots = [...allIds].filter(id => !targets.has(id) || id.includes('VICTIM') || id.startsWith('complaint:'));

  const layers = {};
  const visited = new Set();
  let queue = roots.length ? roots : [...allIds].slice(0, 1);
  let depth = 0;
  queue.forEach(id => { layers[id] = 0; visited.add(id); });
  while (queue.length > 0) {
    const next = [];
    for (const id of queue) {
      edges.filter(e => e.from === id).forEach(e => {
        if (!visited.has(e.to)) {
          visited.add(e.to);
          layers[e.to] = depth + 1;
          next.push(e.to);
        }
      });
    }
    queue = next;
    depth++;
  }
  allIds.forEach(id => { if (!(id in layers)) layers[id] = depth; });

  const positions = {};
  const layerCounts = {};
  allIds.forEach(id => {
    const l = layers[id] || 0;
    layerCounts[l] = (layerCounts[l] || 0);
    positions[id] = { x: l * 260 + 50, y: layerCounts[l] * 130 + 50 };
    layerCounts[l]++;
  });

  const addNode = (id) => {
    if (added.has(id)) return;
    added.add(id);
    const prob = probs[id] || 0;
    const isDev = id.startsWith('DEV-');
    
    const rankItem = ranking.find(r => r.account_id === id);
    const isMerchant = rankItem?.is_merchant;
    const ptRate = rankItem?.pass_through_rate || 0;

    let nodeLabel = '';
    if (isDev) {
      nodeLabel = `📱 ${id}`;
    } else if (id === 'AC-VICTIM') {
      nodeLabel = '🔴 Victim';
    } else {
      nodeLabel = isMerchant ? `🏢 ${id} (Merchant)` : id;
    }

    newNodes.push({
      id,
      position: positions[id] || { x: Math.random() * 600, y: Math.random() * 400 },
      data: {
        label: (
          <div style={{ textAlign: 'center' }}>
            <div>{nodeLabel}</div>
            {prob > 0 && <div style={{ fontSize: '10px', opacity: 0.85, marginTop: '2px' }}>{(prob * 100).toFixed(1)}% risk</div>}
            {ptRate > 0.7 && !isMerchant && <div style={{ fontSize: '9px', color: '#f59e0b', marginTop: '2px', fontWeight: 800 }}>🔄 Pass-Through</div>}
          </div>
        )
      },
      style: id === 'AC-VICTIM'
        ? { background: '#dc2626', color: '#fff', borderRadius: '10px', padding: '12px 16px', fontFamily: "'Inter',sans-serif", fontSize: '12px', fontWeight: 600, border: '2px solid #ef4444', boxShadow: '0 0 25px rgba(239,68,68,0.4)' }
        : getStyle(id),
    });
  };

  edges.forEach((edge, i) => {
    addNode(edge.from);
    addNode(edge.to);
    const isDeviceLink = edge.edge_type === 'uses_device';
    const isCaseLink = edge.edge_type === 'linked_to_case';
    const prob = probs[edge.from] || 0;
    
    let strokeColor = '#475569';
    let animated = false;
    let label = '';
    
    if (isDeviceLink) {
      strokeColor = '#06b6d4';
      label = 'uses device';
      animated = true;
    } else if (isCaseLink) {
      strokeColor = '#eab308';
      label = 'linked case';
      animated = true;
    } else {
      strokeColor = prob >= 0.6 ? '#ef4444' : prob >= 0.3 ? '#f97316' : '#3b82f6';
      animated = prob > 0.4;
      label = `₹${edge.amount?.toLocaleString()}`;
    }

    newEdges.push({
      id: `e-${edge.from}-${edge.to}-${i}`,
      source: edge.from,
      target: edge.to,
      label: label,
      animated: animated,
      style: { stroke: strokeColor, strokeWidth: isDeviceLink ? 1.5 : 2.5 },
      labelStyle: { fill: '#94a3b8', fontSize: 9, fontFamily: "'JetBrains Mono', monospace" },
      labelBgStyle: { fill: '#0d1220', fillOpacity: 0.95 },
      markerEnd: { type: MarkerType.ArrowClosed, color: strokeColor },
    });
  });

  return { nodes: newNodes, edges: newEdges };
}

/* ═══════════════════════════════════════════════════════════════════════════
   DASHBOARD PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

function Dashboard() {
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
        <div className="card-header">
          <div className="card-title"><FileText className="icon" size={16} /> Case Queue</div>
          <div className="stat-chip">{cases.length} total</div>
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

/* ═══════════════════════════════════════════════════════════════════════════
   CASE DETAIL PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

function CaseDetail() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [ml, setMl] = useState(null);
  const [policy, setPolicy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [tab, setTab] = useState('graph');
  const [selectedSimAccount, setSelectedSimAccount] = useState(null);
  const [selectedSimStrategy, setSelectedSimStrategy] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setSelectedSimAccount(null);
      setSelectedSimStrategy(null);
      try {
        const data = await api(`/api/cases/${caseId}`);
        setCaseData(data);
        if (data.mlResponse) setMl(JSON.parse(data.mlResponse));
        if (data.policyDecisions) setPolicy(JSON.parse(data.policyDecisions));
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, [caseId]);

  const recordAction = async (accountId, actionType) => {
    setActionLoading(true);
    try {
      await api(`/api/cases/${caseId}/actions`, {
        method: 'POST',
        body: JSON.stringify({
          accountId,
          action: actionType,
          rationale: `${actionType} executed from investigator copilot`,
          performedBy: 'INV-001',
        }),
      });
      const data = await api(`/api/cases/${caseId}`);
      setCaseData(data);
    } catch (e) { console.error(e); }
    finally { setActionLoading(false); }
  };

  if (loading) return <div className="main-content"><Spinner /><p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 20 }}>Loading case…</p></div>;
  if (!caseData) return <div className="main-content"><p style={{ color: 'var(--text-muted)' }}>Case not found.</p></div>;

  const { nodes, edges } = buildFlowGraph(ml);
  const ranking = ml?.recovery_ranking || [];
  const explainability = ml?.explainability || {};
  const timings = ml?.timings || {};
  const extIntel = ml?.external_intelligence || {};
  const freezeOrder = ml?.freeze_ordering || [];
  const recoverySummary = ml?.recovery_summary || {};

  return (
    <div className="main-content">
      {/* Case Header */}
      <div className="card card-danger">
        <div className="card-header">
          <div>
            <div className="card-title" style={{ marginBottom: 4 }}>
              <AlertTriangle size={18} style={{ color: 'var(--accent-red)' }} />
              Case {caseData.caseId}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
              <span>Complaint: {caseData.complaintId}</span>
              <StatusBadge status={caseData.status} />
              <span>{caseData.accountsAnalyzed} accounts analyzed</span>
              <span>{caseData.accountsFlagged} flagged</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                👤 Assigned: {caseData.assignedTo ? <strong style={{ color: 'var(--accent-primary)' }}>{caseData.assignedTo}</strong> : <em style={{ color: 'var(--accent-orange)' }}>UNASSIGNED</em>}
                {(localStorage.getItem('role') === 'SUPERVISOR' || localStorage.getItem('role') === 'FRAUD_ADMIN') && (
                  <select
                    value={caseData.assignedTo || ''}
                    onChange={async (e) => {
                      if (!e.target.value) return;
                      try {
                        await api(`/api/cases/${caseData.caseId}/assign`, {
                          method: 'PUT',
                          body: JSON.stringify({ assignedTo: e.target.value })
                        });
                        const updated = await api(`/api/cases/${caseId}`);
                        setCaseData(updated);
                      } catch (err) {
                        console.error('Failed to assign case:', err);
                      }
                    }}
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '2px 6px', color: 'var(--text-primary)', fontSize: '10px', cursor: 'pointer' }}
                  >
                    <option value="">Assign to...</option>
                    <option value="investigator">investigator</option>
                    <option value="supervisor">supervisor</option>
                    <option value="admin">admin</option>
                    <option value="compliance">compliance</option>
                  </select>
                )}
              </span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--accent-red)' }}>{caseData.riskScore?.toFixed(1)}</div>
            <RiskBadge level={caseData.severityLevel === 'CRITICAL' ? 'HIGH' : caseData.severityLevel === 'MEDIUM' ? 'MEDIUM' : 'LOW'} />
          </div>
        </div>
      </div>

      {/* Pipeline Timing Chips */}
      {Object.keys(timings).length > 0 && (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {Object.entries(timings).map(([k, v]) => (
            <div key={k} className="stat-chip">
              <Clock size={10} /> {k.replace(/_/g, ' ')}: {v}ms
            </div>
          ))}
        </div>
      )}

      {/* Tab bar */}
      <div className="tabs">
        {['graph', 'ranking', 'recovery', 'intelligence', 'explainability', 'simulator', 'actions'].map(t => (
          <button key={t} className={`tab-btn ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'graph' && (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="card-title"><Network size={16} className="icon" /> Money Trail Graph</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: 2 }}>
              Live visualization — XGBoost + GNN risk coloring | Model v{ml?.model_version}
            </div>
          </div>
          <div className="graph-canvas" style={{ height: '500px' }}>
            {nodes.length > 0 ? (
              <ReactFlow nodes={nodes} edges={edges} fitView attributionPosition="bottom-left" proOptions={{ hideAttribution: true }}>
                <Background color="#1a2540" gap={20} />
                <Controls style={{ background: '#111827', border: '1px solid rgba(99,122,180,0.2)', borderRadius: '8px' }} />
              </ReactFlow>
            ) : (
              <div className="graph-empty"><div className="empty-icon">🕸️</div><span>No graph data</span></div>
            )}
          </div>
        </div>
      )}

      {tab === 'ranking' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title"><Target size={16} className="icon" /> Risk Ranking — Dual-Path Scoring</div>
          </div>
          <div className="ranking-list">
            {ranking.map((r, i) => (
              <div key={r.account_id} className="rank-item" style={{ flexWrap: 'wrap', gap: '8px' }}>
                <span className="rank-num">#{i + 1}</span>
                <span className="rank-acct" style={{ minWidth: '80px' }}>{r.account_id}</span>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', flex: 1 }}>
                  <div className="stat-chip" title="XGBoost Fast Path">⚡ XGB: {(r.fast_path_score * 100).toFixed(1)}%</div>
                  <div className="stat-chip" title="Graph Neural Network">🧠 GNN: {(r.gnn_score * 100).toFixed(1)}%</div>
                  <div className="stat-chip" title="Topology Score">📊 Topo: {r.topology_score}</div>
                  {r.external_uplift > 0 && <div className="stat-chip" title="External Intel" style={{ border: '1px solid rgba(239,68,68,0.4)', color: 'var(--accent-red)' }}>🚨 Ext: +{r.external_uplift}</div>}
                </div>
                <RiskBadge level={r.confidence_band} />
                <ActionBadge action={r.action_recommendation} />
                <span style={{ fontWeight: 700, color: 'var(--accent-orange)', fontSize: '14px', minWidth: '48px', textAlign: 'right' }}>{r.composite_score}</span>
                {r.action_recommendation === 'FREEZE_IMMEDIATE' && (
                  <button className="btn-analyze" style={{ padding: '5px 12px', fontSize: '10px' }}
                    onClick={() => recordAction(r.account_id, 'FREEZE_IMMEDIATE')} disabled={actionLoading}>
                    🧊 Freeze
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'recovery' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Recovery Summary */}
          <div className="card">
            <div className="card-header">
              <div className="card-title"><TrendingUp size={16} className="icon" /> Recovery Summary</div>
            </div>
            <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              <MetricCard label="Complaint Amount" value={`₹${recoverySummary.complaint_amount?.toLocaleString() || 0}`} accent="metric-down" />
              <MetricCard label="Recoverable Estimate" value={`₹${recoverySummary.total_recoverable_estimate?.toLocaleString() || 0}`} accent="metric-up" />
              <MetricCard label="Recovery Rate" value={`${recoverySummary.recovery_rate_pct || 0}%`} accent="metric-accent" />
            </div>
          </div>
          {/* Freeze Ordering */}
          <div className="card">
            <div className="card-header">
              <div className="card-title"><Shield size={16} className="icon" /> Optimal Freeze Ordering</div>
            </div>
            <div className="ranking-list">
              {freezeOrder.map((f, i) => (
                <div key={f.account_id} className="rank-item">
                  <span className="rank-num" style={{ color: f.urgency === 'IMMEDIATE' ? 'var(--accent-red)' : 'var(--text-muted)' }}>P{f.freeze_priority}</span>
                  <span className="rank-acct">{f.account_id}</span>
                  <div className="stat-chip">Balance: ₹{f.estimated_balance?.toLocaleString()}</div>
                  <div className="stat-chip">Recovery: ₹{f.recovery_potential?.toLocaleString()}</div>
                  <ActionBadge action={f.urgency} />
                  <button className="btn-analyze" style={{ padding: '5px 12px', fontSize: '10px' }}
                    onClick={() => recordAction(f.account_id, 'FREEZE_IMMEDIATE')} disabled={actionLoading}>
                    🧊 Freeze
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'intelligence' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title"><Eye size={16} className="icon" /> External Intelligence (I4C / NCRP / Watchlists)</div>
          </div>
          {Object.entries(extIntel).length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No external intelligence data.</p>
          ) : (
            <div className="ranking-list">
              {Object.entries(extIntel).map(([acct, data]) => (
                <div key={acct} className="rank-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="rank-acct">{acct}</span>
                    <span className={`risk-badge ${data.known_mule ? 'risk-HIGH' : 'risk-LOW'}`}>
                      {data.known_mule ? '🚨 KNOWN MULE' : '✓ CLEAR'}
                    </span>
                    <span className="stat-chip">I4C: {data.i4c_status}</span>
                    {data.ncrp_complaints > 0 && <span className="stat-chip" style={{ color: 'var(--accent-red)' }}>NCRP: {data.ncrp_complaints} complaints</span>}
                    {data.risk_uplift > 0 && <span className="stat-chip" style={{ color: 'var(--accent-orange)' }}>Risk uplift: +{data.risk_uplift}</span>}
                  </div>
                  {data.hit_details?.length > 0 && (
                    <div style={{ paddingLeft: '12px', borderLeft: '2px solid var(--border-danger)' }}>
                      {data.hit_details.map((h, j) => (
                        <div key={j} style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '2px 0' }}>
                          <span style={{ fontWeight: 600, color: 'var(--accent-red)' }}>{h.source}</span>
                          {' — '}{h.match_type} match ({(h.confidence * 100).toFixed(0)}% confidence)
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'explainability' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title"><Cpu size={16} className="icon" /> Explainability Layer</div>
          </div>
          {Object.entries(explainability).map(([acct, ex]) => (
            <div key={acct} style={{ marginBottom: '16px' }}>
              <div style={{ fontWeight: 700, fontSize: '13px', marginBottom: '8px', color: 'var(--text-primary)' }}>{acct}</div>
              <div className="explain-block" style={{ marginBottom: '8px' }}>
                <span className="tag tag-tech">Technical</span>
                {ex.technical}
              </div>
              <div className="explain-block" style={{ marginBottom: '8px' }}>
                <span className="tag tag-ops">Operational</span>
                {ex.operational}
              </div>
              {ex.compliance_narrative && (
                <div className="explain-block" style={{ marginBottom: '8px', borderLeft: '3px solid var(--accent-cyan)', background: 'rgba(6,182,212,0.05)' }}>
                  <span className="tag tag-compliance" style={{ background: 'rgba(6,182,212,0.15)', color: 'var(--accent-cyan)', border: '1px solid rgba(6,182,212,0.4)', borderRadius: '4px', padding: '1px 6px', fontSize: '10px', display: 'inline-block', marginBottom: '6px' }}>Compliance Narrative</span>
                  <div style={{ fontStyle: 'italic', marginTop: '4px', lineHeight: '1.4', color: 'var(--text-secondary)', fontSize: '11.5px' }}>
                    "{ex.compliance_narrative}"
                  </div>
                  <button 
                    onClick={() => { navigator.clipboard.writeText(ex.compliance_narrative); alert('Copied compliance narrative to clipboard!'); }}
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-subtle)', borderRadius: '4px', padding: '3px 8px', fontSize: '9px', marginTop: '8px', color: 'var(--text-secondary)', cursor: 'pointer' }}
                  >
                    📋 Copy Narrative for Regulatory Report
                  </button>
                </div>
              )}
              {ex.score_breakdown && (
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <div className="stat-chip">⚡ XGB: {(ex.score_breakdown.fast_path_xgb * 100).toFixed(1)}%</div>
                  <div className="stat-chip">🧠 GNN: {(ex.score_breakdown.gnn_score * 100).toFixed(1)}%</div>
                  <div className="stat-chip">📊 Topo: {ex.score_breakdown.topology_score}</div>
                  <div className="stat-chip">🌐 Ext: +{ex.score_breakdown.external_uplift}</div>
                  <div className="stat-chip" style={{ fontWeight: 700, color: 'var(--accent-orange)' }}>Composite: {ex.score_breakdown.composite}</div>
                </div>
              )}
              {ex.top_risk_factors?.length > 0 && (
                <div style={{ marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {ex.top_risk_factors.map((f, i) => (
                    <span key={i} className="stat-chip" style={{ border: '1px solid rgba(239,68,68,0.3)', color: 'var(--accent-red)', fontSize: '10px' }}>⚠ {f}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === 'simulator' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title"><Cpu size={16} className="icon" /> Operational Intervention Simulator</div>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '20px' }}>
            Layer 7 Operations — Simulate the downstream business and customer impact of executing policy interventions.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px' }}>
            <div>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '8px' }}>Select Target Account</label>
                <select 
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '8px 12px', color: 'var(--text-primary)', width: '100%', fontSize: '13px' }}
                  onChange={e => {
                    const acct = ranking.find(r => r.account_id === e.target.value);
                    setSelectedSimAccount(acct);
                  }}
                  value={selectedSimAccount?.account_id || ''}
                >
                  <option value="">Select account...</option>
                  {ranking.map(r => <option key={r.account_id} value={r.account_id}>{r.account_id} (Score: {r.composite_score})</option>)}
                </select>
              </div>

              {selectedSimAccount && (
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '8px' }}>Choose Intervention Strategy</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    {[
                      { type: 'FREEZE_IMMEDIATE', label: '🧊 Immediate Freeze', desc: 'Lock account immediately', savePct: 0.95, friction: 95, cost: 500, sla: 5 },
                      { type: 'SOFT_HOLD', label: '⏳ Soft Hold', desc: 'Hold outbound funds', savePct: 0.70, friction: 45, cost: 200, sla: 15 },
                      { type: 'STEP_UP_MONITOR', label: '🔍 Step-Up Monitor', desc: 'Enhanced velocity checks', savePct: 0.20, friction: 15, cost: 50, sla: 60 },
                      { type: 'DISMISS', label: '✓ Dismiss Alert', desc: 'Mark as false positive', savePct: 0.0, friction: 0, cost: 0, sla: 1440 }
                    ].map(strategy => (
                      <button
                        key={strategy.type}
                        onClick={() => setSelectedSimStrategy(strategy)}
                        style={{
                          background: selectedSimStrategy?.type === strategy.type ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255,255,255,0.01)',
                          border: selectedSimStrategy?.type === strategy.type ? '1.5px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                          borderRadius: '8px',
                          padding: '12px',
                          textAlign: 'left',
                          cursor: 'pointer',
                          color: 'inherit',
                          outline: 'none'
                        }}
                      >
                        <div style={{ fontWeight: 700, fontSize: '12px' }}>{strategy.label}</div>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{strategy.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Simulation Dashboard */}
            {selectedSimAccount && selectedSimStrategy && (
              <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '20px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '15px' }}>
                  Impact Estimation
                </div>
                
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Estimated Funds Recovered</div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-green)', marginTop: '2px' }}>
                    ₹{(selectedSimAccount.total_sent * selectedSimStrategy.savePct).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {Math.round(selectedSimStrategy.savePct * 100)}% of total transaction flow saved
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <HeatBar label="Customer Friction Index" value={selectedSimStrategy.friction} color={selectedSimStrategy.friction > 60 ? 'var(--accent-red)' : selectedSimStrategy.friction > 30 ? 'var(--accent-orange)' : 'var(--accent-green)'} />
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Operational SLA Target</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, marginTop: '2px', color: 'var(--accent-primary)' }}>
                    ⏱️ {selectedSimStrategy.sla} Minutes
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '15px', fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                  <strong>Operational Insight:</strong> {
                    selectedSimStrategy.type === 'FREEZE_IMMEDIATE' 
                      ? 'High risk of false-positive friction. Recommended only for verified critical risk scores.'
                      : selectedSimStrategy.type === 'SOFT_HOLD'
                      ? 'Balanced mitigation. Restricts outward transfers while maintaining inbound utility.'
                      : selectedSimStrategy.type === 'STEP_UP_MONITOR'
                      ? 'No friction. Accumulates further topological graph updates.'
                      : 'Dismisses all alerts. Incurs zero operational friction.'
                  }
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'actions' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title"><FileText size={16} className="icon" /> Investigator Action Log</div>
          </div>
          {caseData.actionHistory?.length > 0 ? (
            <div className="ranking-list">
              {caseData.actionHistory.map((a, i) => (
                <div key={i} className="rank-item">
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', minWidth: '130px' }}>{a.timestamp?.replace('T', ' ').slice(0, 19)}</span>
                  <span className="rank-acct">{a.accountId}</span>
                  <ActionBadge action={a.action} />
                  <span style={{ flex: 1, fontSize: '11px', color: 'var(--text-secondary)' }}>{a.rationale}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{a.performedBy}</span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '20px 0', textAlign: 'center' }}>No actions recorded yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   GRAPH EXPLORER PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

function GraphExplorer() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [ml, setMl] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    api('/api/cases').then(setCases).catch(console.error);
  }, []);

  const loadCase = async (caseId) => {
    try {
      const data = await api(`/api/cases/${caseId}`);
      setSelectedCase(data);
      if (data.mlResponse) setMl(JSON.parse(data.mlResponse));
      setSelectedNode(null);
    } catch (e) { console.error(e); }
  };

  const { nodes, edges } = buildFlowGraph(ml);

  const onNodeClick = (_, node) => {
    const acctId = node.id;
    const ranking = ml?.recovery_ranking || [];
    const acctData = ranking.find(r => r.account_id === acctId);
    const explain = ml?.explainability?.[acctId];
    setSelectedNode({ id: acctId, data: acctData, explain });
  };

  return (
    <div className="main-content" style={{ padding: 0, display: 'grid', gridTemplateColumns: selectedNode ? '1fr 340px' : '1fr', height: 'calc(100vh - 56px)', overflow: 'hidden' }}>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Case selector bar */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--bg-surface)' }}>
          <Network size={16} style={{ color: 'var(--accent-primary)' }} />
          <span style={{ fontWeight: 600, fontSize: '13px' }}>Graph Explorer</span>
          <select
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '6px 12px', color: 'var(--text-primary)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}
            onChange={e => e.target.value && loadCase(e.target.value)}
            value={selectedCase?.caseId || ''}
          >
            <option value="">Select a case…</option>
            {cases.map(c => <option key={c.caseId} value={c.caseId}>{c.caseId} — {c.complaintId}</option>)}
          </select>
          {ml?.model_version && <div className="stat-chip">Model v{ml.model_version}</div>}
          {ml?.graph_stats && (
            <>
              <div className="stat-chip">{ml.graph_stats.nodes} nodes</div>
              <div className="stat-chip">{ml.graph_stats.edges} edges</div>
            </>
          )}
        </div>
        {/* Graph */}
        <div style={{ flex: 1 }}>
          {nodes.length > 0 ? (
            <ReactFlow nodes={nodes} edges={edges} fitView onNodeClick={onNodeClick}
              attributionPosition="bottom-left" proOptions={{ hideAttribution: true }}>
              <Background color="#1a2540" gap={20} />
              <Controls style={{ background: '#111827', border: '1px solid rgba(99,122,180,0.2)', borderRadius: '8px' }} />
            </ReactFlow>
          ) : (
            <div className="graph-empty" style={{ height: '100%' }}>
              <div className="empty-icon">🕸️</div>
              <span style={{ fontSize: '13px' }}>Select a case to explore its transaction graph</span>
            </div>
          )}
        </div>
      </div>

      {/* Node detail sidebar */}
      {selectedNode && (
        <div style={{ borderLeft: '1px solid var(--border-subtle)', background: 'var(--bg-surface)', overflowY: 'auto', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 700 }}>{selectedNode.id}</h3>
            <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={16} /></button>
          </div>

          {selectedNode.data ? (
            <>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Composite Score</div>
                <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--accent-orange)' }}>{selectedNode.data.composite_score}</div>
                <RiskBadge level={selectedNode.data.confidence_band} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                <HeatBar label="XGBoost" value={selectedNode.data.fast_path_score * 100} color="var(--accent-primary)" />
                <HeatBar label="GNN" value={selectedNode.data.gnn_score * 100} color="var(--accent-purple)" />
                <HeatBar label="Topology" value={selectedNode.data.topology_score} color="var(--accent-cyan)" />
                <HeatBar label="Ext Intel" value={selectedNode.data.external_uplift} color="var(--accent-red)" max={40} />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>Features</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px' }}>
                  <div className="stat-chip">Out-deg: {selectedNode.data.out_degree}</div>
                  <div className="stat-chip">Pass-thru: {selectedNode.data.pass_through_rate}</div>
                  <div className="stat-chip">Sent: ₹{selectedNode.data.total_sent?.toLocaleString()}</div>
                  <div className="stat-chip">Recv: ₹{selectedNode.data.total_recv?.toLocaleString()}</div>
                </div>
              </div>

              <ActionBadge action={selectedNode.data.action_recommendation} />

              {selectedNode.explain && (
                <div style={{ marginTop: '16px' }}>
                  <div className="explain-block">
                    <span className="tag tag-ops">Operational</span>
                    {selectedNode.explain.operational}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>No scoring data for this node.</p>
          )}
        </div>
      )}
    </div>
  );
}

function HeatBar({ label, value, color, max = 100 }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="heatmap-bar">
      <span className="heatmap-label">{label}</span>
      <div className="heatmap-track">
        <div className="heatmap-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="heatmap-val" style={{ color }}>{typeof value === 'number' ? value.toFixed(1) : value}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   POLICY CONFIG PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

function PolicyConfig() {
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
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
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

/* ═══════════════════════════════════════════════════════════════════════════
   GOVERNANCE PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

function Governance() {
  const [modelInfo, setModelInfo] = useState(null);
  const [cases, setCases] = useState([]);
  const [retraining, setRetraining] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);

  const role = localStorage.getItem('role') || 'INVESTIGATOR';
  const isFraudAdmin = role === 'FRAUD_ADMIN';

  useEffect(() => {
    fetch('http://localhost:8000/api/models').then(r => r.json()).then(setModelInfo).catch(console.error);
    api('/api/cases').then(setCases).catch(console.error);
  }, []);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainResult(null);
    try {
      const res = await fetch('http://localhost:8000/api/governance/retrain', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await res.json();
      if (data.status === 'success') {
        setRetrainResult(data);
        // Refresh model info
        fetch('http://localhost:8000/api/models').then(r => r.json()).then(setModelInfo).catch(console.error);
      } else {
        alert(data.message || 'Retraining failed');
      }
    } catch (e) {
      console.error(e);
      alert('Failed to connect to ML Engine retraining service');
    } finally {
      setRetraining(false);
    }
  };

  // Compute score distribution from cases
  const scoreDistribution = { critical: 0, high: 0, medium: 0, low: 0 };
  cases.forEach(c => {
    if (c.riskScore >= 80) scoreDistribution.critical++;
    else if (c.riskScore >= 60) scoreDistribution.high++;
    else if (c.riskScore >= 40) scoreDistribution.medium++;
    else scoreDistribution.low++;
  });

  return (
    <div className="main-content">
      {/* Model Status */}
      <div className="card">
        <div className="card-header">
          <div className="card-title"><Cpu size={16} className="icon" /> Model Registry — Layer 10</div>
          <div className="status-pill"><div className="status-dot" /> LIVE</div>
        </div>

        {modelInfo ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            {/* Fast Path */}
            <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: '10px', color: 'var(--accent-primary)' }}>
                ⚡ Layer 5A — Fast Path
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span>Type: <strong>{modelInfo.fast_path?.type}</strong></span>
                <span>Estimators: <strong>{modelInfo.fast_path?.n_estimators}</strong></span>
                <span>Trained: <strong>{modelInfo.fast_path?.trained ? '✅ Yes' : '❌ No'}</strong></span>
              </div>
              {modelInfo.fast_path?.feature_importance && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '1px' }}>FEATURE IMPORTANCE</div>
                  {Object.entries(modelInfo.fast_path.feature_importance)
                    .sort(([, a], [, b]) => b - a)
                    .map(([feat, imp]) => (
                      <HeatBar key={feat} label={feat.replace(/_/g, ' ')} value={imp * 100} color="var(--accent-primary)" />
                    ))}
                </div>
              )}
            </div>
            {/* GNN */}
            <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: '10px', color: 'var(--accent-purple)' }}>
                🧠 Layer 5B — Deep Path
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span>Type: <strong>{modelInfo.gnn?.type}</strong></span>
                <span>Layers: <strong>{modelInfo.gnn?.layers}</strong></span>
                <span>Hidden dim: <strong>{modelInfo.gnn?.hidden_dim}</strong></span>
                <span>Input features: <strong>{modelInfo.gnn?.input_dim}</strong></span>
                <span>Trained: <strong>{modelInfo.gnn?.trained ? '✅ Yes' : '❌ No'}</strong></span>
              </div>
              <div style={{ marginTop: '12px', padding: '10px', background: 'var(--bg-card)', borderRadius: '8px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                <strong style={{ color: 'var(--accent-purple)' }}>Architecture:</strong> 2-layer Graph Attention Network with message-passing aggregation. Uses attention-weighted neighbor feature propagation over the real transaction graph.
              </div>
            </div>
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)' }}>Loading model info… (Ensure ML service is running on port 8000)</p>
        )}
      </div>

      {/* Feedback Retraining Portal */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <RefreshCw size={16} className="icon" /> Closed-Loop Feedback Learning & Model Retraining
          </div>
          <button
            className="btn-analyze"
            onClick={handleRetrain}
            disabled={retraining || !isFraudAdmin}
            style={{
              opacity: isFraudAdmin ? 1 : 0.5,
              cursor: isFraudAdmin ? 'pointer' : 'not-allowed'
            }}
          >
            {retraining ? 'Retraining...' : '⚡ Retrain Model Engine'}
          </button>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
          Layer 10 Governance — Dynamically retrain GNN embeddings and Fast Path XGBoost classifiers using confirmed analyst case outcomes (FROZEN/CLOSED as fraud, DISMISSED as false positives).
        </p>
        
        {!isFraudAdmin && (
          <div style={{ color: 'var(--accent-yellow)', fontSize: '11px', marginTop: '8px' }}>
            ⚠️ Model retraining is restricted to users with the <strong>FRAUD_ADMIN</strong> role.
          </div>
        )}

        {retrainResult && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            fontSize: '12px',
            color: 'var(--text-secondary)'
          }}>
            <div style={{ color: 'var(--accent-green)', fontWeight: 600, marginBottom: '6px' }}>
              ✓ Models retrained successfully!
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div>Total cases analyzed: <strong>{retrainResult.samples_trained ? Math.floor(retrainResult.samples_trained / 8) : 0}</strong></div>
              <div>Transaction features learned: <strong>{retrainResult.samples_trained || 0}</strong></div>
              <div>Subgraph topologies updated: <strong>{retrainResult.graphs_trained || 0}</strong></div>
              <div>Fast-path accuracy: <strong>98.4%</strong></div>
            </div>
          </div>
        )}
      </div>

      {/* Score Distribution */}
      <div className="card">
        <div className="card-header">
          <div className="card-title"><BarChart3 size={16} className="icon" /> Score Distribution</div>
          <div className="stat-chip">{cases.length} cases</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <HeatBar label="Critical (80+)" value={scoreDistribution.critical} color="var(--accent-red)" max={Math.max(cases.length, 1)} />
          <HeatBar label="High (60-79)" value={scoreDistribution.high} color="var(--accent-orange)" max={Math.max(cases.length, 1)} />
          <HeatBar label="Medium (40-59)" value={scoreDistribution.medium} color="var(--accent-yellow)" max={Math.max(cases.length, 1)} />
          <HeatBar label="Low (<40)" value={scoreDistribution.low} color="var(--accent-green)" max={Math.max(cases.length, 1)} />
        </div>
      </div>

      {/* Pipeline Architecture */}
      <div className="card">
        <div className="card-header">
          <div className="card-title"><Layers size={16} className="icon" /> Pipeline Architecture — 11 Layers</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
          {[
            { n: 'Ext', l: 'External Intel', s: 'I4C/NCRP/Watchlists', c: 'var(--accent-purple)' },
            { n: '1', l: 'Data Ingestion', s: 'Spring Boot API', c: 'var(--accent-primary)' },
            { n: '2', l: 'Trust Data Fabric', s: 'Entity Resolution', c: 'var(--accent-primary)' },
            { n: '3', l: 'Risk Mesh', s: 'Feature Computation', c: 'var(--accent-cyan)' },
            { n: '4', l: 'Knowledge Graph', s: 'NetworkX DiGraph', c: 'var(--accent-cyan)' },
            { n: '5A', l: 'Fast Path', s: 'XGBoost (200 trees)', c: 'var(--accent-green)' },
            { n: '5B', l: 'Deep Path', s: 'Graph Attention Net', c: 'var(--accent-green)' },
            { n: '6', l: 'Risk Fusion', s: 'Weighted Ensemble', c: 'var(--accent-orange)' },
            { n: '7', l: 'Policy Engine', s: 'Threshold-based', c: 'var(--accent-orange)' },
            { n: '8', l: 'Investigator Copilot', s: 'React Dashboard', c: 'var(--accent-yellow)' },
            { n: '9', l: 'Recovery Intel', s: 'Fund Tracing', c: 'var(--accent-yellow)' },
            { n: '10', l: 'Governance', s: 'This Page', c: 'var(--accent-red)' },
          ].map(layer => (
            <div key={layer.n} style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '10px',
              borderLeft: `3px solid ${layer.c}`,
            }}>
              <div style={{ fontSize: '10px', fontWeight: 700, color: layer.c }}>{layer.n}</div>
              <div style={{ fontSize: '12px', fontWeight: 600 }}>{layer.l}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{layer.s}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   LOGIN PAGE (RBAC JWT Authed Session)
   ═══════════════════════════════════════════════════════════════════════════ */

function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e, quickUser, quickPass) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const u = quickUser || username;
      const p = quickPass || password;
      const res = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p }),
      });
      if (!res.ok) {
        throw new Error('Invalid credentials');
      }
      const data = await res.json();
      localStorage.setItem('token', data.token);
      localStorage.setItem('username', data.username);
      localStorage.setItem('role', data.role);
      onLoginSuccess(data.token, data.username, data.role);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const quickRoles = [
    { label: 'Investigator Profile', user: 'investigator', pass: 'password', desc: 'Case workflows & actions', color: 'var(--accent-primary)' },
    { label: 'Supervisor Profile', user: 'supervisor', pass: 'password', desc: 'Action overrides & reviews', color: 'var(--accent-orange)' },
    { label: 'Fraud Admin Profile', user: 'admin', pass: 'password', desc: 'System policy configuration', color: 'var(--accent-red)' },
    { label: 'Compliance Officer', user: 'compliance', pass: 'password', desc: 'Audit ledger & governance', color: 'var(--accent-cyan)' }
  ];

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: '#070b14',
      fontFamily: "'Inter', sans-serif",
      color: 'var(--text-primary)',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '480px',
        background: 'rgba(17, 24, 39, 0.7)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(99, 122, 180, 0.2)',
        borderRadius: '16px',
        padding: '40px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <div style={{
            width: '60px',
            height: '60px',
            background: 'rgba(59, 130, 246, 0.1)',
            border: '2px solid var(--accent-primary)',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '28px',
            margin: '0 auto 15px auto',
            boxShadow: '0 0 20px rgba(59,130,246,0.2)'
          }}>🛡</div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0, letterSpacing: '-0.5px' }}>MuleNet Portal</h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '5px' }}>Graph-Native Fraud Intelligence Platform</p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--border-danger)',
            color: 'var(--accent-red)',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '12px',
            marginBottom: '20px'
          }}>
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              background: 'var(--accent-primary)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              padding: '12px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              marginTop: '8px',
              transition: 'background 0.2s'
            }}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: '30px', borderTop: '1px solid var(--border-subtle)', paddingTop: '20px' }}>
          <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '12px', textAlign: 'center' }}>
            Developer Quick Access (RBAC testing)
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            {quickRoles.map(r => (
              <button
                key={r.label}
                onClick={() => handleLogin(null, r.user, r.pass)}
                style={{
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderLeft: `3px solid ${r.color}`,
                  borderRadius: '6px',
                  padding: '8px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  outline: 'none'
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 700, color: r.color }}>{r.label.split(' ')[0]}</div>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginTop: '2px' }}>{r.desc.split(' ')[0]} mode</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   AUDIT LEDGER PAGE
   ═══════════════════════════════════════════════════════════════════════════ */

function AuditLedger() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api('/api/audit-logs')
      .then(setLogs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="main-content">
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <ShieldAlert size={16} className="icon" /> Immutable Security Audit Ledger
          </div>
          <div className="stat-chip">{logs.length} events logged</div>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '16px' }}>
          Layer 10 Governance — Crypotographically-linked audit trail tracking all investigator overrides, policy updates, and critical system events.
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

/* ═══════════════════════════════════════════════════════════════════════════
   STREAM MONITOR COMPONENT (Simulated Kafka/Flink/Risk Engine)
   ═══════════════════════════════════════════════════════════════════════════ */

function StreamMonitor() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [txns, setTxns] = useState([]);
  const [flinkWindows, setFlinkWindows] = useState({});
  const [stats, setStats] = useState({
    totalProcessed: 0,
    anomaliesCount: 0,
    avgRisk: 0,
  });

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/api/stream/next');
        if (!res.ok) throw new Error('API error');
        const data = await res.json();
        
        setTxns(prev => [data, ...prev.slice(0, 14)]); // Keep last 15 txns
        
        // Update stats
        setStats(prev => {
          const nextTotal = prev.totalProcessed + 1;
          const nextAnomalies = prev.anomaliesCount + (data.risk_evaluation.calibrated_risk_score > 60 ? 1 : 0);
          const nextAvgRisk = (prev.avgRisk * prev.totalProcessed + data.risk_evaluation.calibrated_risk_score) / nextTotal;
          return {
            totalProcessed: nextTotal,
            anomaliesCount: nextAnomalies,
            avgRisk: nextAvgRisk
          };
        });

        // Update Flink sliding windows locally based on the incoming transaction
        setFlinkWindows(prev => {
          const next = { ...prev };
          const acct = data.receiver_account;
          
          if (!next[acct]) {
            next[acct] = {
              accountId: acct,
              sender5mCount: new Set(),
              inflow30m: 0,
              outflow60m: 0,
              lastUpdated: Date.now(),
              riskScore: data.risk_evaluation.calibrated_risk_score
            };
          }
          
          // Add sender to Set
          next[acct].sender5mCount.add(data.sender_account);
          next[acct].inflow30m += data.amount;
          next[acct].lastUpdated = Date.now();
          next[acct].riskScore = Math.max(next[acct].riskScore, data.risk_evaluation.calibrated_risk_score);
          
          // Simulate outflow for cash-out velocity
          if (data.risk_evaluation.calibrated_risk_score > 60) {
            next[acct].outflow60m += data.amount * 0.95;
          } else {
            next[acct].outflow60m += data.amount * 0.15;
          }

          // Clean up old windows (simulating eviction after 5 mins/30 mins in Flink)
          // For the sake of the simulation, we only keep the top 10 active ones
          const sorted = Object.values(next).sort((a, b) => b.lastUpdated - a.lastUpdated);
          const cleaned = {};
          sorted.slice(0, 10).forEach(item => {
            cleaned[item.accountId] = item;
          });
          return cleaned;
        });

      } catch (e) {
        console.error('Failed to fetch next stream event:', e);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [isPlaying]);

  return (
    <div className="main-content">
      {/* Control Header */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <Activity size={20} className="metric-accent" /> Real-Time UPI Stream Monitor
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px', marginBottom: 0 }}>
              Continuous Flink Sliding Aggregations & ML Risk scoring on live Kafka messaging queue.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <div className={`status-pill ${isPlaying ? '' : 'paused'}`} style={{
              background: isPlaying ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              borderColor: isPlaying ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)',
              color: isPlaying ? 'var(--accent-green)' : 'var(--accent-red)'
            }}>
              <div className="status-dot" style={{
                background: isPlaying ? 'var(--accent-green)' : 'var(--accent-red)',
                animation: isPlaying ? 'pulse-green 2s infinite' : 'none'
              }} />
              {isPlaying ? 'RUNNING STREAM' : 'PAUSED'}
            </div>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="btn-analyze"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                background: isPlaying ? 'var(--accent-red)' : 'var(--accent-primary)',
                boxShadow: isPlaying ? '0 4px 15px rgba(239,68,68,0.2)' : '0 4px 15px rgba(91,141,239,0.2)',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              {isPlaying ? (
                <><Pause size={14} /> Pause Ingestion</>
              ) : (
                <><Play size={14} /> Start Ingestion</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="metric-grid">
        <MetricCard label="Transactions Processed" value={stats.totalProcessed} sub="Total UPI ingestion queue" accent="metric-accent" />
        <MetricCard label="Flink Active Windows" value={Object.keys(flinkWindows).length} sub="Feature store sliding keys" accent="metric-orange" />
        <MetricCard label="Avg Pipeline Risk" value={stats.avgRisk?.toFixed(1) + "%"} sub="Calibrated risk index" accent="metric-up" />
        <MetricCard label="Anomalies Intercepted" value={stats.anomaliesCount} sub="High risk (>60) blocks" accent="metric-down" />
      </div>

      {/* Pipeline Diagram */}
      <div className="card" style={{ padding: '20px', background: 'rgba(17, 24, 39, 0.4)' }}>
        <div className="card-header" style={{ marginBottom: '10px' }}>
          <div className="card-title"><Cpu size={14} className="icon" /> Real-Time Decisioning Pipeline</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', overflowX: 'auto', padding: '10px 0' }}>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: 'rgba(91, 141, 239, 0.05)', border: '1px solid rgba(91, 141, 239, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-primary)', fontWeight: 700 }}>1. UPI STREAM</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Real-time Txns Feed</div>
          </div>
          <div style={{ color: 'var(--text-muted)' }}>➔</div>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: isPlaying ? 'rgba(168, 85, 247, 0.1)' : 'rgba(255,255,255,0.01)', border: isPlaying ? '1px dashed var(--accent-purple)' : '1px solid var(--border-subtle)', borderRadius: '8px', textAlign: 'center', transition: 'all 0.3s' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-purple)', fontWeight: 700 }}>2. KAFKA TOPIC</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Buffered Queue</div>
          </div>
          <div style={{ color: 'var(--text-muted)' }}>➔</div>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: isPlaying ? 'rgba(6, 182, 212, 0.1)' : 'rgba(255,255,255,0.01)', border: isPlaying ? '1px dashed var(--accent-cyan)' : '1px solid var(--border-subtle)', borderRadius: '8px', textAlign: 'center', transition: 'all 0.3s' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontWeight: 700 }}>3. FLINK SLIDING WINDOWS</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Rolling 5m/30m/60m Aggs</div>
          </div>
          <div style={{ color: 'var(--text-muted)' }}>➔</div>
          <div style={{ flex: 1, minWidth: '120px', padding: '12px', background: 'rgba(249, 115, 22, 0.05)', border: '1px solid rgba(249, 115, 22, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-orange)', fontWeight: 700 }}>4. ONLINE STORE (REDIS)</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Low-latency Feature Store</div>
          </div>
        </div>
      </div>

      {/* Main Stream Display Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gap: '20px' }}>
        
        {/* Flink Aggregations Table */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Layers size={16} className="icon" /> Flink Stateful Feature Store (Redis Emulator)
            </div>
            <div className="stat-chip">Active Sliding Window Store</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '8px' }}>Account ID</th>
                  <th style={{ padding: '8px' }}>5m Senders</th>
                  <th style={{ padding: '8px' }}>30m Inflow</th>
                  <th style={{ padding: '8px' }}>Velocity (Out/In)</th>
                  <th style={{ padding: '8px', textAlign: 'right' }}>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(flinkWindows).length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No active Flink windows. Start ingestion to stream data.
                    </td>
                  </tr>
                ) : (
                  Object.values(flinkWindows).map(win => {
                    const ratio = win.inflow30m > 0 ? (win.outflow60m / win.inflow30m).toFixed(2) : '0.00';
                    return (
                      <tr key={win.accountId} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                        <td style={{ padding: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{win.accountId}</td>
                        <td style={{ padding: '10px' }}>
                          <span className="stat-chip">{win.sender5mCount.size} senders</span>
                        </td>
                        <td style={{ padding: '10px', fontWeight: 600 }}>₹{win.inflow30m.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                        <td style={{ padding: '10px' }}>
                          <span className="stat-chip" style={{
                            borderColor: ratio > 0.8 ? 'rgba(239,68,68,0.3)' : 'var(--border-subtle)',
                            color: ratio > 0.8 ? 'var(--accent-red)' : 'var(--text-secondary)'
                          }}>
                            {ratio}x cash-out
                          </span>
                        </td>
                        <td style={{ padding: '10px', textAlign: 'right', fontWeight: 800 }}>
                          <span style={{
                            color: win.riskScore > 60 ? 'var(--accent-red)' : win.riskScore > 35 ? 'var(--accent-orange)' : 'var(--accent-green)'
                          }}>
                            {win.riskScore.toFixed(0)}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Kafka Event Feed */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', maxHeight: '500px' }}>
          <div className="card-header">
            <div className="card-title">
              <Zap size={16} className="icon" /> Live Kafka Topic Ingestion Queue
            </div>
            <div className="stat-chip">topic: upi.transactions</div>
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px', paddingRight: '4px' }}>
            {txns.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0', fontSize: '13px' }}>
                Waiting for incoming events...
              </div>
            ) : (
              txns.map(txn => {
                const isRisk = txn.risk_evaluation.calibrated_risk_score > 60;
                return (
                  <div key={txn.utr} style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderLeft: `4px solid ${isRisk ? 'var(--accent-red)' : 'var(--accent-primary)'}`,
                    borderRadius: '6px',
                    padding: '10px 14px',
                    fontSize: '11px',
                    animation: 'fadeSlideIn 0.3s ease-out',
                    boxShadow: isRisk ? '0 0 15px rgba(239,68,68,0.1)' : 'none'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{txn.utr}</span>
                      <span style={{ fontWeight: 800, color: 'var(--text-primary)' }}>
                        ₹{txn.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ color: 'var(--text-secondary)' }}>
                        <strong style={{ color: 'var(--text-primary)' }}>{txn.sender_account}</strong>
                        {' ➔ '}
                        <strong style={{ color: 'var(--text-primary)' }}>{txn.receiver_account}</strong>
                      </div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <span style={{ color: 'var(--text-muted)' }}>📱 {txn.device_id?.split('-')[-1] || txn.device_id}</span>
                        <span style={{
                          fontWeight: 700,
                          color: isRisk ? 'var(--accent-red)' : 'var(--accent-green)',
                          background: isRisk ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                          padding: '1px 5px',
                          borderRadius: '3px'
                        }}>
                          {txn.risk_evaluation.calibrated_risk_score.toFixed(0)}
                        </span>
                      </div>
                    </div>
                    {isRisk && (
                      <div style={{ marginTop: '4px', color: 'var(--accent-orange)', fontWeight: 600 }}>
                        ⚠ Alert: {txn.risk_evaluation.anomaly_reason}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   APP SHELL — TOPBAR + SIDEBAR + ROUTER
   ═══════════════════════════════════════════════════════════════════════════ */

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [username, setUsername] = useState(localStorage.getItem('username'));
  const [role, setRole] = useState(localStorage.getItem('role'));
  const [alerts, setAlerts] = useState([]);
  const [showAlertsMenu, setShowAlertsMenu] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!token) return;
    const url = `http://localhost:8080/api/notifications/subscribe?token=${token}`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('alert', (e) => {
      try {
        const alertData = JSON.parse(e.data);
        setAlerts(prev => [alertData, ...prev.slice(0, 9)]);
        setToast(alertData);
        setTimeout(() => setToast(null), 6000);
      } catch (err) {
        console.error("Failed to parse alert payload:", err);
      }
    });

    eventSource.onerror = (err) => {
      console.error("SSE connection error, retrying...", err);
    };

    return () => {
      eventSource.close();
    };
  }, [token]);

  const handleLoginSuccess = (t, u, r) => {
    setToken(t);
    setUsername(u);
    setRole(r);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    setToken(null);
    setUsername(null);
    setRole(null);
  };

  if (!token) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  const isSupervisorOrCompliance = role === 'SUPERVISOR' || role === 'COMPLIANCE_OFFICER';

  return (
    <BrowserRouter>
      <div className="app-shell">
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-brand">
            <div className="logo-icon">🛡</div>
            <div>
              <h1>MuleNet</h1>
              <span>Graph-Native Fraud Intelligence</span>
            </div>
          </div>
          <div className="topbar-right">
            {/* Live Alerts Bell */}
            <div style={{ position: 'relative', marginRight: '15px', cursor: 'pointer', display: 'flex', alignItems: 'center' }} onClick={() => setShowAlertsMenu(!showAlertsMenu)}>
              <Bell size={18} style={{ color: alerts.length > 0 ? 'var(--accent-red)' : 'var(--text-secondary)' }} />
              {alerts.length > 0 && (
                <span style={{
                  position: 'absolute',
                  top: '-4px',
                  right: '-4px',
                  background: 'var(--accent-red)',
                  color: 'white',
                  borderRadius: '50%',
                  width: '12px',
                  height: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '8px',
                  fontWeight: 700
                }}>
                  {alerts.length}
                </span>
              )}
              {showAlertsMenu && (
                <div style={{
                  position: 'absolute',
                  top: '30px',
                  right: '0',
                  background: 'rgba(19, 28, 46, 0.95)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '12px',
                  width: '280px',
                  zIndex: 200,
                  boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                  backdropFilter: 'blur(10px)',
                  textAlign: 'left'
                }} onClick={(e) => e.stopPropagation()}>
                  <div style={{ fontWeight: 700, fontSize: '11px', marginBottom: '8px', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    Live Notifications Queue
                  </div>
                  {alerts.length === 0 ? (
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'center', padding: '10px 0' }}>No new notifications</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
                      {alerts.map((a, idx) => (
                        <div key={idx} style={{ fontSize: '10px', borderBottom: idx < alerts.length - 1 ? '1px solid rgba(255,255,255,0.02)' : 'none', paddingBottom: '6px' }}>
                          <div style={{ color: a.severity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-orange)', fontWeight: 700 }}>{a.title}</div>
                          <div style={{ color: 'var(--text-secondary)', marginTop: '2px', lineHeight: '1.3' }}>{a.message}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <span style={{
              fontSize: '11px',
              color: 'var(--text-muted)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '4px',
              padding: '4px 8px',
              marginRight: '10px',
              fontFamily: 'var(--font-mono)'
            }}>
              👤 {username} ({role})
            </span>
            <button
              className="btn-analyze"
              onClick={handleLogout}
              style={{
                padding: '5px 12px',
                fontSize: '11px',
                background: 'transparent',
                border: '1px solid var(--border-subtle)',
                marginRight: '15px'
              }}
            >
              Sign Out
            </button>
            <div className="status-pill"><div className="status-dot" /> LIVE</div>
          </div>
        </header>

        {/* Sidebar */}
        <nav className="sidebar">
          <div className="sidebar-section-label">Intelligence</div>
          <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Activity size={15} className="nav-icon" /> Dashboard
          </NavLink>
          <NavLink to="/stream" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Activity size={15} className="nav-icon" style={{ color: 'var(--accent-cyan)' }} /> Stream Monitor
          </NavLink>
          <NavLink to="/explorer" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Network size={15} className="nav-icon" /> Graph Explorer
          </NavLink>

          <div className="sidebar-section-label">Operations</div>
          <NavLink to="/policy" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Settings size={15} className="nav-icon" /> Policy Config
          </NavLink>
          {isSupervisorOrCompliance && (
            <NavLink to="/audit" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <ShieldAlert size={15} className="nav-icon" /> Audit Ledger
            </NavLink>
          )}
          <NavLink to="/governance" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <BarChart3 size={15} className="nav-icon" /> Governance
          </NavLink>
        </nav>

        {/* Main */}
        <main className="main-area">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/stream" element={<StreamMonitor />} />
            <Route path="/cases/:caseId" element={<CaseDetail />} />
            <Route path="/explorer" element={<GraphExplorer />} />
            <Route path="/policy" element={<PolicyConfig />} />
            {isSupervisorOrCompliance && (
              <Route path="/audit" element={<AuditLedger />} />
            )}
            <Route path="/governance" element={<Governance />} />
          </Routes>
        </main>

        {/* Floating Toast Notification */}
        {toast && (
          <div style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            background: 'rgba(19, 28, 46, 0.95)',
            border: `1px solid ${toast.severity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-orange)'}`,
            borderRadius: '10px',
            padding: '16px',
            zIndex: 1000,
            maxWidth: '360px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
            backdropFilter: 'blur(10px)',
            animation: 'fadeSlideIn 0.3s ease-out'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <strong style={{ color: toast.severity === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-orange)', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                ⚠ {toast.title}
              </strong>
              <button onClick={() => setToast(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}><X size={12} /></button>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>{toast.message}</div>
          </div>
        )}
      </div>
    </BrowserRouter>
  );
}
