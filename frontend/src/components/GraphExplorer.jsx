import React, { useState, useEffect } from 'react';
import { Network, X } from 'lucide-react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import {
  api, RiskBadge, ActionBadge, buildFlowGraph, HeatBar
} from './Common';

export default function GraphExplorer() {
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
