import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useNavigate, useParams } from 'react-router-dom';
import {
  ShieldAlert, Activity, Search, AlertTriangle, Layers, MapPin,
  BarChart3, Settings, Eye, Network, TrendingUp, Clock, Target,
  ChevronRight, Zap, Shield, FileText, Bell, RefreshCw, ArrowRight,
  X, CheckCircle, XCircle, Pause, AlertCircle, Cpu, GitBranch
} from 'lucide-react';
import ReactFlow, { Background, Controls, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import { testIntakeRequest } from './testData';

/* ═══════════════════════════════════════════════════════════════════════════
   API HELPER
   ═══════════════════════════════════════════════════════════════════════════ */

const API = 'http://localhost:8080';

async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
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
    DISMISSED: 'var(--text-muted)',
  };
  return (
    <span className="risk-badge" style={{
      background: `${colors[status] || 'var(--text-muted)'}20`,
      color: colors[status] || 'var(--text-muted)',
      border: `1px solid ${colors[status] || 'var(--text-muted)'}50`,
    }}>
      {status}
    </span>
  );
}

function Spinner() {
  return <div className="loading-bar" style={{ width: '100%' }} />;
}

/* ═══════════════════════════════════════════════════════════════════════════
   GRAPH CANVAS (shared by CaseDetail + GraphExplorer)
   ═══════════════════════════════════════════════════════════════════════════ */

function buildFlowGraph(mlData) {
  if (!mlData) return { nodes: [], edges: [] };
  const newNodes = [];
  const newEdges = [];
  const added = new Set();
  const probs = mlData.mule_probabilities || {};

  const getStyle = (id) => {
    const r = probs[id] || 0;
    if (r >= 0.7) return { background: '#ef4444', color: '#fff', borderRadius: '10px', padding: '12px 16px', fontFamily: "'Inter',sans-serif", fontSize: '12px', fontWeight: 600, border: '2px solid rgba(239,68,68,0.5)', boxShadow: '0 0 20px rgba(239,68,68,0.3)' };
    if (r >= 0.4) return { background: '#f97316', color: '#fff', borderRadius: '10px', padding: '12px 16px', fontFamily: "'Inter',sans-serif", fontSize: '12px', fontWeight: 600, border: '2px solid rgba(249,115,22,0.5)', boxShadow: '0 0 15px rgba(249,115,22,0.2)' };
    if (r > 0.15) return { background: '#eab308', color: '#000', borderRadius: '10px', padding: '12px 16px', fontFamily: "'Inter',sans-serif", fontSize: '12px', fontWeight: 600, border: '2px solid rgba(234,179,8,0.5)' };
    return { background: '#3b82f6', color: '#fff', borderRadius: '10px', padding: '12px 16px', fontFamily: "'Inter',sans-serif", fontSize: '12px', fontWeight: 600, border: '2px solid rgba(59,130,246,0.4)' };
  };

  // Layout: arrange in rows by hop depth
  const positions = {};
  const edges = mlData.suspicious_edges || [];
  const sources = new Set(edges.map(e => e.from));
  const targets = new Set(edges.map(e => e.to));
  const allIds = new Set([...sources, ...targets]);
  const roots = [...allIds].filter(id => !targets.has(id) || id.includes('VICTIM'));

  // BFS layering
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
  // Assign positions unvisited nodes
  allIds.forEach(id => { if (!(id in layers)) layers[id] = depth; });

  const layerCounts = {};
  allIds.forEach(id => {
    const l = layers[id] || 0;
    layerCounts[l] = (layerCounts[l] || 0);
    positions[id] = { x: l * 250 + 50, y: layerCounts[l] * 120 + 50 };
    layerCounts[l]++;
  });

  const addNode = (id) => {
    if (added.has(id)) return;
    added.add(id);
    const prob = probs[id] || 0;
    newNodes.push({
      id,
      position: positions[id] || { x: Math.random() * 600, y: Math.random() * 400 },
      data: {
        label: (
          <div style={{ textAlign: 'center' }}>
            <div>{id === 'AC-VICTIM' ? '🔴 Victim' : id}</div>
            {prob > 0 && <div style={{ fontSize: '10px', opacity: 0.85, marginTop: '2px' }}>{(prob * 100).toFixed(1)}% risk</div>}
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
    const prob = probs[edge.from] || 0;
    newEdges.push({
      id: `e-${edge.from}-${edge.to}-${i}`,
      source: edge.from,
      target: edge.to,
      label: `₹${edge.amount?.toLocaleString()}`,
      animated: prob > 0.4,
      style: { stroke: prob >= 0.6 ? '#ef4444' : prob >= 0.3 ? '#f97316' : '#475569', strokeWidth: 2 },
      labelStyle: { fill: '#94a3b8', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" },
      labelBgStyle: { fill: '#0d1220', fillOpacity: 0.9 },
      markerEnd: { type: MarkerType.ArrowClosed, color: prob >= 0.6 ? '#ef4444' : '#475569' },
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
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        api('/api/cases'),
        api('/api/cases/stats/summary'),
      ]);
      setCases(c);
      setStats(s);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

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

  useEffect(() => {
    (async () => {
      setLoading(true);
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
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', gap: '16px', alignItems: 'center' }}>
              <span>Complaint: {caseData.complaintId}</span>
              <StatusBadge status={caseData.status} />
              <span>{caseData.accountsAnalyzed} accounts analyzed</span>
              <span>{caseData.accountsFlagged} flagged</span>
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
        {['graph', 'ranking', 'recovery', 'intelligence', 'explainability', 'actions'].map(t => (
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
    <div className="main-content" style={{ padding: 0, display: 'grid', gridTemplateColumns: selectedNode ? '1fr 340px' : '1fr', height: '100%' }}>
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

  useEffect(() => {
    fetch('http://localhost:8000/api/models').then(r => r.json()).then(setModelInfo).catch(console.error);
    api('/api/cases').then(setCases).catch(console.error);
  }, []);

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
   APP SHELL — TOPBAR + SIDEBAR + ROUTER
   ═══════════════════════════════════════════════════════════════════════════ */

export default function App() {
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
            <div className="status-pill"><div className="status-dot" /> LIVE</div>
            <div className="avatar">INV</div>
          </div>
        </header>

        {/* Sidebar */}
        <nav className="sidebar">
          <div className="sidebar-section-label">Intelligence</div>
          <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Activity size={15} className="nav-icon" /> Dashboard
          </NavLink>
          <NavLink to="/explorer" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Network size={15} className="nav-icon" /> Graph Explorer
          </NavLink>

          <div className="sidebar-section-label">Operations</div>
          <NavLink to="/policy" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Settings size={15} className="nav-icon" /> Policy Config
          </NavLink>
          <NavLink to="/governance" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <BarChart3 size={15} className="nav-icon" /> Governance
          </NavLink>
        </nav>

        {/* Main */}
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cases/:caseId" element={<CaseDetail />} />
          <Route path="/explorer" element={<GraphExplorer />} />
          <Route path="/policy" element={<PolicyConfig />} />
          <Route path="/governance" element={<Governance />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
