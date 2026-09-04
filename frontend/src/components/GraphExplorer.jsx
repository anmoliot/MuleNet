import React, { useState, useEffect } from 'react';
import { Network, X } from 'lucide-react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import {
  api, RiskBadge, ActionBadge, buildFlowGraph, HeatBar
} from './Common';
import { Button, Alert } from '@mui/material';

export default function GraphExplorer() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [ml, setMl] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [emptyError, setEmptyError] = useState('');
  const [loadingCase, setLoadingCase] = useState(false);
  const [showLegend, setShowLegend] = useState(false);

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
    } catch (e) {
      console.error(e);
    }
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
                  // Direct fallback for instant demo
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
              <div className="stat-chip">{ml.graph_stats.edges} edges</div>
            </>
          )}
        </div>

        {/* Total rupees moved chip + risk legend toggle */}
        {ml?.suspicious_edges && (
          <div style={{ padding: '8px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', gap: 16, alignItems: 'center', fontSize: 12, background: 'rgba(15, 23, 42, 0.6)' }}>
            <span style={{ fontWeight: 700 }}>₹ moved: {ml.suspicious_edges.reduce((s, e) => s + (e.amount || 0), 0).toLocaleString()}</span>
            <button onClick={() => setShowLegend(v => !v)} style={{ background: 'none', border: 'none', color: 'var(--accent-cyan)', cursor: 'pointer', textDecoration: 'underline' }}>
              {showLegend ? 'Hide legend' : 'Risk legend'}
            </button>
            {showLegend && (
              <span style={{ display: 'inline-flex', gap: 10, alignItems: 'center' }}>
                <span style={{ color: '#ef4444' }}>■ high</span>
                <span style={{ color: '#f97316' }}>■ medium/mule</span>
                <span style={{ color: '#3b82f6' }}>■ low</span>
                <span style={{ color: '#06b6d4' }}>■ device link</span>
              </span>
            )}
          </div>
        )}

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
              <span style={{ fontSize: '13px' }}>{emptyError || 'Select a case to explore its transaction graph'}</span>
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
