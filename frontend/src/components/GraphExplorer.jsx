import React, { useState, useEffect, useMemo } from 'react';
import {
  Network, X, IndianRupee, ArrowRightLeft, ArrowDownLeft, ArrowUpRight,
  TrendingUp, Layers, ShieldAlert, Activity, ArrowRight, ShieldCheck,
  AlertTriangle, Filter
} from 'lucide-react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import {
  api, RiskBadge, ActionBadge, buildFlowGraph, HeatBar,
  MoneyFlowEdge, formatINR, formatINRCompact
} from './Common';
import { Button } from '@mui/material';

export default function GraphExplorer() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [ml, setMl] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [emptyError, setEmptyError] = useState('');
  const [loadingCase, setLoadingCase] = useState(false);
  const [filterThreshold, setFilterThreshold] = useState(0);

  const edgeTypes = useMemo(() => ({ moneyFlow: MoneyFlowEdge }), []);

  useEffect(() => {
    api('/api/cases')
      .then(list => {
        const arr = Array.isArray(list) ? list : [];
        setCases(arr);
        if (!arr || arr.length === 0) {
          setEmptyError('No cases yet');
        } else {
          setEmptyError('');
          loadCase(arr[0].caseId);
        }
      })
      .catch(e => {
        console.error(e);
        setEmptyError('Backend unreachable or no cases seeded.');
      });
  }, []);

  const loadCase = async (caseId) => {
    try {
      const data = await api(`/api/cases/${caseId}`);
      setSelectedCase(data);
      if (data && data.mlResponse) {
        const parsed = typeof data.mlResponse === 'string' ? JSON.parse(data.mlResponse) : data.mlResponse;
        setMl(parsed);
      }
      setSelectedNode(null);
      setSelectedEdge(null);
    } catch (e) {
      console.error(e);
    }
  };

  const rawGraph = useMemo(() => buildFlowGraph(ml), [ml]);

  // Optionally filter or mark edges based on threshold
  const { nodes, edges } = useMemo(() => {
    if (!filterThreshold) return rawGraph;
    const filteredEdges = rawGraph.edges.map(edge => {
      const amt = Number(edge.data?.amount || 0);
      if (amt > 0 && amt < filterThreshold) {
        return {
          ...edge,
          style: { ...edge.style, opacity: 0.25 },
        };
      }
      return edge;
    });
    return { nodes: rawGraph.nodes, edges: filteredEdges };
  }, [rawGraph, filterThreshold]);

  // Flow telemetry metrics
  const suspiciousEdges = ml?.suspicious_edges || [];
  const totalMoved = suspiciousEdges.reduce((s, e) => s + (Number(e.amount) || 0), 0);
  const transferHops = suspiciousEdges.filter(e => !e.edge_type || e.edge_type === 'transfer');
  const hopCount = transferHops.length;
  const amounts = transferHops.map(e => Number(e.amount) || 0).filter(a => a > 0);
  const maxHop = amounts.length > 0 ? Math.max(...amounts) : 0;
  const avgHop = hopCount > 0 ? totalMoved / hopCount : 0;
  const compactTotal = formatINRCompact(totalMoved);

  const onNodeClick = (_, node) => {
    const acctId = node.id;
    const ranking = ml?.recovery_ranking || [];
    const acctData = ranking.find(r => r.account_id === acctId);
    const explain = ml?.explainability?.[acctId];
    setSelectedNode({ id: acctId, data: acctData, explain });
    setSelectedEdge(null);
  };

  const onEdgeClick = (_, edge) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
  };

  const onPaneClick = () => {
    setSelectedNode(null);
    setSelectedEdge(null);
  };

  // Connected edges for the selected node
  const nodeEdges = selectedNode
    ? suspiciousEdges.filter(e => e.from === selectedNode.id || e.to === selectedNode.id)
    : [];

  const sidebarOpen = !!(selectedNode || selectedEdge);

  return (
    <div
      className="main-content"
      style={{
        padding: 0,
        display: 'grid',
        gridTemplateColumns: sidebarOpen ? '1fr 360px' : '1fr',
        height: 'calc(100vh - 56px)',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minWidth: 0 }}>
        {/* Case selector bar */}
        <div
          style={{
            padding: '10px 20px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            background: 'var(--bg-surface)',
            flexWrap: 'wrap',
          }}
        >
          <Network size={16} style={{ color: 'var(--accent-primary)' }} />
          <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--text-primary)' }}>Mule Flow Explorer</span>
          <select
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '6px 12px',
              color: 'var(--text-primary)',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
            }}
            onChange={e => e.target.value && loadCase(e.target.value)}
            value={selectedCase?.caseId || ''}
          >
            <option value="">Select a case…</option>
            {cases.map(c => (
              <option key={c.caseId} value={c.caseId}>
                {c.caseId} — {c.complaintId}
              </option>
            ))}
          </select>

          {emptyError && (
            <Button
              size="small"
              variant="contained"
              color="warning"
              disabled={loadingCase}
              onClick={async () => {
                setLoadingCase(true);
                try {
                  await api('/api/demo/seed', { method: 'POST' });
                  const list = await api('/api/cases');
                  const arr = Array.isArray(list) ? list : [];
                  setCases(arr);
                  setEmptyError('');
                  if (arr.length > 0) {
                    loadCase(arr[0].caseId);
                  }
                } catch (e) {
                  console.error(e);
                  const fallback = await api('/api/cases/CASE-001');
                  if (fallback) {
                    setSelectedCase(fallback);
                    if (fallback.mlResponse) {
                      setMl(typeof fallback.mlResponse === 'string' ? JSON.parse(fallback.mlResponse) : fallback.mlResponse);
                    }
                    setEmptyError('');
                  }
                } finally {
                  setLoadingCase(false);
                }
              }}
            >
              {loadingCase ? 'Seeding…' : 'Generate demo case'}
            </Button>
          )}

          {ml?.model_version && <div className="stat-chip">Model v{ml.model_version}</div>}
          {ml?.graph_stats && (
            <>
              <div className="stat-chip">{ml.graph_stats.nodes} nodes</div>
              <div className="stat-chip">{ml.graph_stats.edges} hops</div>
            </>
          )}

          {/* Quick filter for high-value transfers */}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setFilterThreshold(t => (t === 0 ? 50000 : 0))}
              style={{
                background: filterThreshold > 0 ? 'rgba(249, 115, 22, 0.2)' : 'var(--bg-elevated)',
                border: filterThreshold > 0 ? '1px solid #f97316' : '1px solid var(--border-subtle)',
                color: filterThreshold > 0 ? '#fdba74' : 'var(--text-secondary)',
                borderRadius: '6px',
                padding: '4px 10px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <Filter size={11} />
              {filterThreshold > 0 ? 'Highlighting > ₹50,000' : 'Filter > ₹50k'}
            </button>
          </div>
        </div>

        {/* Amount Moved Hero & Telemetry Bar */}
        {suspiciousEdges.length > 0 && (
          <div className="flow-telemetry-bar">
            {/* Hero Amount Moved Card */}
            <div className="hero-amount-card">
              <div className="hero-icon-wrap">
                <IndianRupee size={18} />
              </div>
              <div className="hero-content">
                <div className="hero-label">Total Dispersal Volume</div>
                <div className="hero-value-row">
                  <span className="hero-amount">
                    ₹{totalMoved.toLocaleString('en-IN')}
                  </span>
                  {compactTotal && (
                    <span className="hero-compact-pill">{compactTotal}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Secondary Dispersal Telemetry */}
            <div className="flow-metric-item">
              <div className="metric-label">Largest Hop</div>
              <div className="metric-val text-amber">
                ₹{maxHop.toLocaleString('en-IN')}
              </div>
            </div>

            <div className="flow-metric-item">
              <div className="metric-label">Transfer Hops</div>
              <div className="metric-val text-blue">
                {hopCount} transactions
              </div>
            </div>

            <div className="flow-metric-item">
              <div className="metric-label">Hop Velocity</div>
              <div className="metric-val text-green">
                ₹{Math.round(avgHop).toLocaleString('en-IN')} / hop
              </div>
            </div>

            {/* Risk Legend */}
            <div className="flow-legend-pills">
              <span className="legend-chip legend-critical">
                <span className="dot">●</span> High Risk Hop
              </span>
              <span className="legend-chip legend-mule">
                <span className="dot">●</span> Mule Layering
              </span>
              <span className="legend-chip legend-normal">
                <span className="dot">●</span> Normal Hop
              </span>
              <span className="legend-chip legend-device">
                <span className="dot">●</span> Device Linked
              </span>
            </div>
          </div>
        )}

        {/* Graph Canvas */}
        <div style={{ flex: 1, position: 'relative' }}>
          {nodes.length > 0 ? (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              edgeTypes={edgeTypes}
              fitView
              onNodeClick={onNodeClick}
              onEdgeClick={onEdgeClick}
              onPaneClick={onPaneClick}
              attributionPosition="bottom-left"
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#1a2540" gap={20} />
              <Controls
                style={{
                  background: '#111827',
                  border: '1px solid rgba(99,122,180,0.2)',
                  borderRadius: '8px',
                }}
              />
            </ReactFlow>
          ) : (
            <div className="graph-empty" style={{ height: '100%' }}>
              <div className="empty-icon">🕸️</div>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                {emptyError || 'Select a case to explore its transaction graph'}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Sidebar: Selected Node Details */}
      {selectedNode && (
        <div
          style={{
            borderLeft: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)',
            overflowY: 'auto',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                Account Dossier
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {selectedNode.id}
              </h3>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <X size={15} />
            </button>
          </div>

          {selectedNode.data ? (
            <>
              {/* Composite Risk Score */}
              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  borderRadius: '10px',
                  padding: '14px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>COMPOSITE RISK SCORE</span>
                  <RiskBadge level={selectedNode.data.confidence_band} />
                </div>
                <div style={{ fontSize: '32px', fontWeight: 900, color: 'var(--accent-orange)', fontFamily: 'var(--font-mono)' }}>
                  {selectedNode.data.composite_score}
                </div>
              </div>

              {/* Cash Flow Dynamics (Inflow / Outflow / Velocity) */}
              <div className="node-flow-section">
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.6px',
                    marginBottom: '10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <ArrowRightLeft size={13} style={{ color: 'var(--accent-cyan)' }} />
                  Cash Flow Dynamics
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                  {/* Inflow Card */}
                  <div className="flow-card flow-card-in">
                    <div className="flow-card-head">
                      <ArrowDownLeft size={13} className="flow-icon in" />
                      <span>TOTAL INFLOW</span>
                    </div>
                    <div className="flow-card-val in">
                      +₹{Number(selectedNode.data.total_recv || 0).toLocaleString('en-IN')}
                    </div>
                  </div>

                  {/* Outflow Card */}
                  <div className="flow-card flow-card-out">
                    <div className="flow-card-head">
                      <ArrowUpRight size={13} className="flow-icon out" />
                      <span>DISPERSED (OUT)</span>
                    </div>
                    <div className="flow-card-val out">
                      -₹{Number(selectedNode.data.total_sent || 0).toLocaleString('en-IN')}
                    </div>
                  </div>
                </div>

                {/* Pass-Through Laundering Gauge */}
                <div className="passthrough-gauge-wrap">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Mule Velocity (Pass-Through)</span>
                    <span
                      style={{
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        color: (selectedNode.data.pass_through_rate || 0) > 0.7 ? '#f97316' : '#38bdf8',
                      }}
                    >
                      {((selectedNode.data.pass_through_rate || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="passthrough-track">
                    <div
                      className="passthrough-fill"
                      style={{
                        width: `${Math.min(100, (selectedNode.data.pass_through_rate || 0) * 100)}%`,
                        background:
                          (selectedNode.data.pass_through_rate || 0) > 0.7
                            ? 'linear-gradient(90deg, #f97316, #ef4444)'
                            : 'linear-gradient(90deg, #3b82f6, #06b6d4)',
                      }}
                    />
                  </div>
                  {(selectedNode.data.pass_through_rate || 0) > 0.7 && (
                    <div style={{ fontSize: '10px', color: '#fb923c', marginTop: '6px', fontWeight: 600 }}>
                      ⚡ Rapid Layering: {((selectedNode.data.pass_through_rate || 0) * 100).toFixed(0)}% funds drained immediately
                    </div>
                  )}
                </div>

                {/* Direct Hop Ledger */}
                {nodeEdges.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <div
                      style={{
                        fontSize: '10px',
                        color: 'var(--text-muted)',
                        marginBottom: '6px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        fontWeight: 700,
                      }}
                    >
                      Direct Hop Ledger ({nodeEdges.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {nodeEdges.map((e, idx) => {
                        const isIncoming = e.to === selectedNode.id;
                        return (
                          <div key={idx} className={`hop-ledger-item ${isIncoming ? 'hop-in' : 'hop-out'}`}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              {isIncoming ? <ArrowDownLeft size={12} color="#22c55e" /> : <ArrowUpRight size={12} color="#f97316" />}
                              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                                {isIncoming ? `From ${e.from}` : `To ${e.to}`}
                              </span>
                            </div>
                            <span className={`hop-amt ${isIncoming ? 'amt-in' : 'amt-out'}`}>
                              {isIncoming ? '+' : '-'}₹{Number(e.amount || 0).toLocaleString('en-IN')}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Model Ensemble Breakdown */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: 700 }}>
                  Model Confidence Weights
                </div>
                <HeatBar label="XGBoost Fast-Path" value={selectedNode.data.fast_path_score * 100} color="var(--accent-primary)" />
                <HeatBar label="GNN Subgraph" value={selectedNode.data.gnn_score * 100} color="var(--accent-purple)" />
                <HeatBar label="Topology Centrality" value={selectedNode.data.topology_score} color="var(--accent-cyan)" />
                <HeatBar label="External Intelligence" value={selectedNode.data.external_uplift} color="var(--accent-red)" max={40} />
              </div>

              {/* Action Recommendation */}
              <div style={{ marginTop: '4px' }}>
                <ActionBadge action={selectedNode.data.action_recommendation} />
              </div>

              {selectedNode.explain && (
                <div className="explain-block" style={{ marginTop: '4px' }}>
                  <span className="tag tag-ops">Operational Narrative</span>
                  {selectedNode.explain.operational}
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              No telemetry scoring profile available for node <strong>{selectedNode.id}</strong>.
            </div>
          )}
        </div>
      )}

      {/* Sidebar: Selected Edge Transfer Hop Inspector */}
      {selectedEdge && !selectedNode && (
        <div
          style={{
            borderLeft: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)',
            overflowY: 'auto',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                Hop Telemetry
              </div>
              <h3 style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-primary)' }}>
                Transfer Hop Inspector
              </h3>
            </div>
            <button
              onClick={() => setSelectedEdge(null)}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '6px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <X size={15} />
            </button>
          </div>

          {/* Big Amount Moved Box */}
          <div className="edge-inspector-amount-box">
            <div style={{ fontSize: '10px', fontWeight: 700, color: '#6ee7b7', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '4px' }}>
              Amount Moved on Hop
            </div>
            <div className="edge-inspector-amount-val">
              ₹{Number(selectedEdge.data?.amount || 0).toLocaleString('en-IN')}
            </div>
            <div style={{ marginTop: '4px', fontSize: '11px', color: '#a7f3d0', fontFamily: 'var(--font-mono)' }}>
              {formatINRCompact(selectedEdge.data?.amount)}
            </div>
          </div>

          {/* Transfer Route */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              borderRadius: '8px',
              padding: '12px',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 700 }}>
              Transaction Vector
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>ORIGIN</div>
                <div style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                  {selectedEdge.data?.from || selectedEdge.source}
                </div>
              </div>
              <ArrowRight size={18} style={{ color: selectedEdge.data?.prob >= 0.6 ? '#ef4444' : '#38bdf8' }} />
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>DESTINATION</div>
                <div style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                  {selectedEdge.data?.to || selectedEdge.target}
                </div>
              </div>
            </div>
          </div>

          {/* Hop Risk Assessment */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.55)',
              borderRadius: '8px',
              padding: '12px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 700, marginBottom: '8px' }}>
              ML Hop Risk Classification
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span
                style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontSize: '10px',
                  fontWeight: 800,
                  background: (selectedEdge.data?.prob || 0) >= 0.6 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                  color: (selectedEdge.data?.prob || 0) >= 0.6 ? '#fca5a5' : '#7dd3fc',
                  border: `1px solid ${(selectedEdge.data?.prob || 0) >= 0.6 ? '#ef4444' : '#38bdf8'}`,
                }}
              >
                {(selectedEdge.data?.prob || 0) >= 0.6 ? 'CRITICAL DISPERSAL' : 'STANDARD HOP'}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {((selectedEdge.data?.prob || 0) * 100).toFixed(1)}% Suspicion
              </span>
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              {(selectedEdge.data?.prob || 0) >= 0.6
                ? 'High-velocity payout along the layering path. Rapidly drains the complaint victim amount.'
                : 'Transaction edge captured by subgraph expansion for contextual intelligence.'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
