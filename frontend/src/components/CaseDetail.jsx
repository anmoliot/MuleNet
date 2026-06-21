import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  AlertTriangle, Clock, Network, Target, TrendingUp, Shield, Eye, Cpu, FileText, X, ChevronRight
} from 'lucide-react';
import ReactFlow, { Background, Controls, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import {
  api, Spinner, MetricCard, RiskBadge, ActionBadge, StatusBadge, HeatBar, buildFlowGraph
} from './Common';

export default function CaseDetail() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [ml, setMl] = useState(null);
  const [policy, setPolicy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [tab, setTab] = useState('graph');
  const [selectedSimAccount, setSelectedSimAccount] = useState(null);
  const [selectedSimStrategy, setSelectedSimStrategy] = useState(null);

  // Comments state
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');

  const loadCase = useCallback(async () => {
    setLoading(true);
    setSelectedSimAccount(null);
    setSelectedSimStrategy(null);
    try {
      const data = await api(`/api/cases/${caseId}`);
      setCaseData(data);
      if (data.mlResponse) setMl(JSON.parse(data.mlResponse));
      if (data.policyDecisions) setPolicy(JSON.parse(data.policyDecisions));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const loadComments = useCallback(async () => {
    try {
      const data = await api(`/api/cases/${caseId}/comments`);
      setComments(data);
    } catch (e) {
      console.error("Failed to load comments:", e);
    }
  }, [caseId]);

  useEffect(() => {
    loadCase();
    loadComments();
  }, [loadCase, loadComments]);

  const submitComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      await api(`/api/cases/${caseId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ commentText: newComment.trim() })
      });
      setNewComment('');
      loadComments();
    } catch (err) {
      console.error("Failed to submit comment:", err);
    }
  };

  const recordAction = async (accountId, actionType) => {
    setActionLoading(true);
    try {
      await api(`/api/cases/${caseId}/actions`, {
        method: 'POST',
        body: JSON.stringify({
          accountId,
          action: actionType,
          rationale: `${actionType} executed from investigator copilot`,
          performedBy: localStorage.getItem('username') || 'INV-001',
        }),
      });
      const data = await api(`/api/cases/${caseId}`);
      setCaseData(data);
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
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

      {/* Case Comments Section */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <div className="card-title"><FileText size={16} className="icon" /> Analyst Comments & Updates Timeline</div>
        </div>
        
        {/* Comment input form */}
        <form onSubmit={submitComment} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input 
            type="text" 
            placeholder="Add operational update, comment, or case note..."
            value={newComment}
            onChange={e => setNewComment(e.target.value)}
            style={{
              flex: 1,
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '10px 14px',
              color: 'var(--text-primary)',
              fontSize: '13px',
              outline: 'none'
            }}
          />
          <button 
            type="submit" 
            className="btn-analyze"
            style={{ padding: '8px 16px', minWidth: '120px' }}
          >
            Add Note
          </button>
        </form>

        {/* Timeline list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {comments.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '12px', textAlign: 'center', padding: '10px 0' }}>
              No updates recorded for this case yet.
            </p>
          ) : (
            comments.map((comment, index) => (
              <div key={comment.id || index} style={{
                display: 'flex',
                gap: '12px',
                background: 'rgba(255,255,255,0.01)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '12px'
              }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'rgba(91, 141, 239, 0.1)',
                  border: '1px solid var(--accent-primary)',
                  color: 'var(--accent-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  flexShrink: 0
                }}>
                  {comment.username?.charAt(0).toUpperCase() || 'A'}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {comment.username}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {comment.createdAt ? new Date(comment.createdAt).toLocaleString() : ''}
                    </span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                    {comment.commentText}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}
